// pqmc2.cc - packet-level multicast source-authentication deployment sim.
// ns-3.41. Tracks, per block: data completion D_i, signature availability S_i,
// and the joint delivered-and-authenticated event; chain (IP-fragmented),
// per-signature, and MTU-aware FEC carries with optional cross-block interleaving.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/error-model.h"
#include "ns3/random-variable-stream.h"
#include "ns3/ipv4-static-routing-helper.h"
#include <iostream>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <cmath>
using namespace ns3;

static uint32_t H_=32;

struct BlockTag : public Tag {
  uint32_t block=0; uint8_t kind=0;
  BlockTag(){} BlockTag(uint32_t b,uint8_t k):block(b),kind(k){}
  static TypeId GetTypeId(){ static TypeId t=TypeId("BlockTag2").SetParent<Tag>()
     .AddConstructor<BlockTag>(); return t; }
  TypeId GetInstanceTypeId() const override { return GetTypeId(); }
  uint32_t GetSerializedSize() const override { return 5; }
  void Serialize(TagBuffer b) const override { b.WriteU32(block); b.WriteU8(kind); }
  void Deserialize(TagBuffer b) override { block=b.ReadU32(); kind=b.ReadU8(); }
  void Print(std::ostream&os) const override { os<<"b="<<block<<" k="<<(int)kind; }
};

// Gilbert-Elliott burst loss (good/bad), stationary mean = meanLoss.
class GELossModel : public ErrorModel {
public:
  static TypeId GetTypeId(){ static TypeId t=TypeId("GELoss2").SetParent<ErrorModel>()
     .AddConstructor<GELossModel>(); return t; }
  GELossModel(){}
  GELossModel(double meanLoss,double meanBurst,uint64_t seed){
    m_pbg=1.0/meanBurst; double PB=std::min(meanLoss,0.999);
    m_pgb=PB/(1-PB)*m_pbg;
    m_r=CreateObject<UniformRandomVariable>();
    m_r->SetAttribute("Min",DoubleValue(0)); m_r->SetAttribute("Max",DoubleValue(1));
    m_r->SetStream(seed);
  }
  bool DoCorrupt(Ptr<Packet>) override {
    double u=m_r->GetValue();
    m_bad = m_bad ? (u>=m_pbg) : (u<m_pgb);
    return m_bad;
  }
  void DoReset() override { m_bad=false; }
private:
  bool m_bad=false; double m_pg=0.0,m_pb=1.0,m_pgb=0.0,m_pbg=0.2;
  Ptr<UniformRandomVariable> m_r;
};

struct Cfg {
  uint32_t sigSize=2420,n=64,d=3,t=8,M=20,payload=1200,blocks=30;
  double verifyUs=30.0,loss=0.0,rttMs=20.0,fecR=0.25,burstLen=5.0;
  uint32_t burst=0,ileave=0,chunkC=1400,seed=1;
  std::string lastRate="10Mbps",mode="chain",tag="x";
} cfg;

// record application length M_sigma and chunk counts
static uint32_t Msigma(){ return cfg.sigSize+cfg.t*H_+8; }   // +8 key id
static uint32_t kChunks(){ return std::max(1u,
  (uint32_t)std::ceil(Msigma()/(double)cfg.chunkC)); }

static double Median(std::vector<double> v){ if(v.empty())return 0;
  std::sort(v.begin(),v.end()); size_t s=v.size();
  return s%2? v[s/2] : (v[s/2-1]+v[s/2])/2; }
static double Pct(std::vector<double> v,double q){ if(v.empty())return 0;
  std::sort(v.begin(),v.end()); size_t idx=(size_t)(q*(v.size()-1)); return v[idx]; }

class Rx : public Application {
public:
  Rx(Ipv4Address group,uint32_t port):m_group(group),m_port(port){}
  uint64_t rxBytes=0,dataRx=0,verifies=0;
  std::vector<double> authMs;
  double lastVerified=0;
  // per-block bookkeeping
  std::map<uint32_t,uint32_t> dataGot;   // block -> data packets present
  std::set<uint32_t> dataComplete;
  std::set<uint32_t> sigAvail;
  std::set<uint32_t> bothAuth;
  uint32_t blocksInRange(){
    uint32_t lo=cfg.mode=="persig"?0:2;
    return cfg.blocks>lo? cfg.blocks-lo:0;
  }
  double MedianAuth(){ return Median(authMs)*1000.0; }
  double P95Auth(){ return Pct(authMs,0.95)*1000.0; }
private:
  struct Job{ bool chain; uint32_t block; double enq; };
  Ipv4Address m_group; uint32_t m_port; Ptr<Socket> m_sock;
  bool m_busy=false; std::vector<Job> m_q;
  std::map<uint32_t,std::vector<double>> m_arr;  // block -> data arrival times
  std::map<uint32_t,uint32_t> m_sigGot;          // block -> coded chunks
  std::set<uint32_t> m_recon;
  uint32_t m_pendingSig=0;                        // chain: block awaiting its sig
  virtual void StartApplication(){
    m_sock=Socket::CreateSocket(GetNode(),UdpSocketFactory::GetTypeId());
    m_sock->Bind(InetSocketAddress(m_group,m_port));
    m_sock->SetRecvCallback(MakeCallback(&Rx::Recv,this));
  }
  void NoteData(uint32_t b,double now){
    if(dataComplete.count(b)) return;
    dataGot[b]++;
    m_arr[b].push_back(now);
    if(dataGot[b]>=cfg.n){
      dataComplete.insert(b);
      if(cfg.mode=="persig"){
        // each packet carries and has a valid per-packet signature
        if(!bothAuth.count(b)) bothAuth.insert(b);
      } else TryBoth(b,now);
    }
  }
  void NoteSig(uint32_t b,double now){
    if(!sigAvail.count(b)){ sigAvail.insert(b); }
    TryBoth(b,now);
  }
  void TryBoth(uint32_t b,double now){
    if(dataComplete.count(b)&&sigAvail.count(b)&&!bothAuth.count(b)){
      bothAuth.insert(b);
      m_q.push_back({true,b,now});
      Pump();
    }
  }
  void Recv(Ptr<Socket> s){
    Address from; Ptr<Packet> p;
    uint32_t dataSize=cfg.payload+(cfg.mode=="persig"?cfg.sigSize:cfg.d*H_);
    double now=Simulator::Now().GetSeconds();
    while((p=s->RecvFrom(from))){
      if(p->GetSize()<1)continue; rxBytes+=p->GetSize();
      BlockTag tg; bool hasTag=p->PeekPacketTag(tg);
      if(cfg.mode=="persig"){
        dataRx++;
        if(hasTag) NoteData(tg.block,now);
        m_q.push_back({false,0,now});
      } else if(cfg.mode=="fec"){
        if(!hasTag) continue;
        if(tg.kind==0){ dataRx++; NoteData(tg.block,now); }
        else {
          m_sigGot[tg.block]++;
          uint32_t k=kChunks();
          if(m_sigGot[tg.block]>=k && !m_recon.count(tg.block)){
            m_recon.insert(tg.block); NoteSig(tg.block,now);
          }
        }
      } else { // chain: data packets tagged; reassembled sig packet is large
        if(hasTag && tg.kind==0){ dataRx++; NoteData(tg.block,now); }
        else if(p->GetSize()==dataSize){ dataRx++; NoteData(m_pendingSig,now); }
        else { NoteSig(m_pendingSig,now); m_pendingSig++; }
      }
    }
    Pump();
  }
  void Pump(){
    if(m_busy||m_q.empty())return;
    m_busy=true; Job j=m_q.front();
    Simulator::Schedule(MicroSeconds(cfg.verifyUs),&Rx::Done,this,j);
  }
  void Done(Job j){
    m_q.erase(m_q.begin()); m_busy=false;
    double now=Simulator::Now().GetSeconds();
    verifies++; lastVerified=now;
    if(j.chain){
      for(double a:m_arr[j.block]) authMs.push_back(now-a);
      m_arr.erase(j.block);
    } else authMs.push_back(now-j.enq);
    Pump();
  }
};

class Tx : public Application {
public:
  Tx(Address dst):m_dst(dst){}
private:
  Address m_dst; Ptr<Socket> m_sock;
  struct Ev{ uint32_t size,block; uint8_t kind; };
  virtual void StartApplication(){
    m_sock=Socket::CreateSocket(GetNode(),UdpSocketFactory::GetTypeId());
    m_sock->Bind(); m_sock->Connect(m_dst);
    double rateBps=DataRate(cfg.lastRate).GetBitRate()/8.0;
    uint32_t dataSize=cfg.payload+(cfg.mode=="persig"?cfg.sigSize:cfg.d*H_);
    uint32_t sigWire=Msigma()+64;
    double base=Simulator::Now().GetSeconds();
    std::vector<Ev> ev;
    if(cfg.mode=="fec"){
      uint32_t k=kChunks(),tot=k+(uint32_t)std::ceil(cfg.fecR*k);
      std::map<uint32_t,std::vector<Ev>> bucket;
      for(uint32_t b=0;b<cfg.blocks;b++){
        for(uint32_t i=0;i<cfg.n;i++) ev.push_back({dataSize,b,0});
        for(auto&ch:bucket[b]) ev.push_back(ch);
        for(uint32_t m=0;m<tot;m++){
          Ev e{cfg.chunkC,b,1};
          if(cfg.ileave==0){ ev.push_back(e); continue; }
          uint32_t tgt=b+1+(uint32_t)std::floor((double)m*cfg.ileave/tot);
          if(tgt<cfg.blocks) bucket[tgt].push_back(e); else ev.push_back(e);
        }
      }
    } else {
      for(uint32_t b=0;b<cfg.blocks;b++){
        for(uint32_t i=0;i<cfg.n;i++) ev.push_back({dataSize,b,0});
        if(cfg.mode=="chain") ev.push_back({sigWire,b,1});
      }
    }
    double t=0.001;
    for(Ev e:ev){
      Simulator::Schedule(Seconds(base+t),&Tx::SendTagged,this,e.size,e.block,e.kind);
      t+=e.size/rateBps;
    }
  }
  void SendTagged(uint32_t sz,uint32_t b,uint8_t kind){
    Ptr<Packet> p=Create<Packet>(sz); p->AddPacketTag(BlockTag(b,kind)); m_sock->Send(p);
  }
};

int main(int argc,char*argv[]){
  CommandLine cmd;
  cmd.AddValue("sigSize","sig bytes",cfg.sigSize); cmd.AddValue("n","block",cfg.n);
  cmd.AddValue("d","per-pkt hashes",cfg.d); cmd.AddValue("t","record hashes",cfg.t);
  cmd.AddValue("M","receivers",cfg.M);
  cmd.AddValue("payload","payload",cfg.payload); cmd.AddValue("blocks","blocks",cfg.blocks);
  cmd.AddValue("verifyUs","verify us",cfg.verifyUs); cmd.AddValue("loss","loss",cfg.loss);
  cmd.AddValue("rttMs","rtt",cfg.rttMs); cmd.AddValue("lastRate","rate",cfg.lastRate);
  cmd.AddValue("mode","chain|persig|fec",cfg.mode); cmd.AddValue("tag","tag",cfg.tag);
  cmd.AddValue("fecR","redundancy",cfg.fecR);
  cmd.AddValue("burst","burst flag",cfg.burst);
  cmd.AddValue("burstLen","mean burst length",cfg.burstLen);
  cmd.AddValue("ileave","interleave depth",cfg.ileave);
  cmd.AddValue("chunkC","FEC chunk bytes",cfg.chunkC);
  cmd.AddValue("seed","rng seed",cfg.seed);
  cmd.Parse(argc,argv);

  uint32_t K=10, D=(cfg.M+K-1)/K;
  NodeContainer nodes; nodes.Create(2+D+cfg.M);
  auto S=nodes.Get(0), core=nodes.Get(1);
  auto router=[&](uint32_t i){return nodes.Get(2+i);};
  auto recv=[&](uint32_t i){return nodes.Get(2+D+i);};

  PointToPointHelper backbone; backbone.SetDeviceAttribute("DataRate",StringValue("100Mbps"));
  backbone.SetChannelAttribute("Delay",StringValue("2ms"));
  PointToPointHelper lastmile; lastmile.SetDeviceAttribute("DataRate",StringValue(cfg.lastRate));
  char delay[32]; snprintf(delay,32,"%fms",cfg.rttMs/2.0);
  lastmile.SetChannelAttribute("Delay",StringValue(delay));

  InternetStackHelper inet; inet.Install(nodes);
  Ipv4AddressHelper ip; uint32_t subnet=1; Ipv4StaticRoutingHelper srh;

  NetDeviceContainer sCore=backbone.Install(S,core);
  ip.SetBase("10.0.1.0","255.255.255.0"); ip.Assign(sCore); subnet=2;

  std::vector<NetDeviceContainer> coreLinks(D);
  std::vector<std::vector<NetDeviceContainer>> leafLinks(D);
  for(uint32_t dr=0;dr<D;dr++){
    coreLinks[dr]=backbone.Install(core,router(dr));
    ip.SetBase(("10.0."+std::to_string(subnet)+".0").c_str(),"255.255.255.0");
    ip.Assign(coreLinks[dr]); subnet++;
    uint32_t k=std::min(K,cfg.M-dr*K); leafLinks[dr].resize(k);
    for(uint32_t j=0;j<k;j++){
      leafLinks[dr][j]=lastmile.Install(router(dr),recv(dr*K+j));
      if(cfg.loss>0){
        Ptr<ErrorModel> em;
        uint64_t ls=1000u*cfg.seed+dr*101u+j;
        if(cfg.burst) em=CreateObject<GELossModel>(cfg.loss,cfg.burstLen,ls);
        else {
          Ptr<RateErrorModel> r=CreateObject<RateErrorModel>();
          r->SetUnit(RateErrorModel::ERROR_UNIT_PACKET); r->SetRate(cfg.loss);
          r->SetRandomVariable(CreateObjectWithAttributes<UniformRandomVariable>(
             "Min",DoubleValue(0),"Max",DoubleValue(1)));
          r->AssignStreams(ls);
          em=r;
        }
        leafLinks[dr][j].Get(1)->SetAttribute("ReceiveErrorModel",PointerValue(em));
      }
      ip.SetBase(("10.0."+std::to_string(subnet)+".0").c_str(),"255.255.255.0");
      ip.Assign(leafLinks[dr][j]); subnet++;
    }
  }

  Ipv4Address group("239.9.9.9");
  { Ptr<Ipv4> ipS=S->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> srS=srh.GetStaticRouting(ipS);
    srS->SetDefaultRoute(Ipv4Address("10.0.1.2"),1); }
  { Ptr<Ipv4> ipC=core->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> srC=srh.GetStaticRouting(ipC);
    uint32_t coreIn=ipC->GetInterfaceForDevice(sCore.Get(1));
    std::vector<uint32_t> out;
    for(uint32_t dr=0;dr<D;dr++)
      out.push_back(ipC->GetInterfaceForDevice(coreLinks[dr].Get(0)));
    srC->AddMulticastRoute(Ipv4Address("10.0.1.1"),group,coreIn,out); }
  for(uint32_t dr=0;dr<D;dr++){
    Ptr<Ipv4> ipR=router(dr)->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> sr=srh.GetStaticRouting(ipR);
    uint32_t inIf=ipR->GetInterfaceForDevice(coreLinks[dr].Get(1));
    std::vector<uint32_t> out; uint32_t k=std::min(K,cfg.M-dr*K);
    for(uint32_t j=0;j<k;j++)
      out.push_back(ipR->GetInterfaceForDevice(leafLinks[dr][j].Get(0)));
    sr->AddMulticastRoute(Ipv4Address("10.0.1.1"),group,inIf,out);
  }

  uint32_t port=7000;
  Ptr<Tx> tx=CreateObject<Tx>(Address(InetSocketAddress(group,port)));
  S->AddApplication(tx); tx->SetStartTime(Seconds(0.2));
  std::vector<Ptr<Rx>> rxs;
  for(uint32_t i=0;i<cfg.M;i++){
    Ptr<Rx> r=CreateObject<Rx>(group,port); recv(i)->AddApplication(r);
    r->SetStartTime(Seconds(0)); rxs.push_back(r);
  }
  double perBlock;
  if(cfg.mode=="chain") perBlock=cfg.n*(cfg.payload+cfg.d*H_)+(Msigma()+64);
  else if(cfg.mode=="fec"){
    uint32_t k=kChunks(),tot=k+(uint32_t)std::ceil(cfg.fecR*k);
    perBlock=cfg.n*(cfg.payload+cfg.d*H_)+(uint64_t)tot*cfg.chunkC;
  } else perBlock=cfg.n*(cfg.payload+cfg.sigSize);
  double stopT=cfg.blocks*perBlock/(DataRate(cfg.lastRate).GetBitRate()/8.0)+8;
  Simulator::Stop(Seconds(stopT)); Simulator::Run(); Simulator::Destroy();

  // aggregate over receivers
  double sumMed=0,sumP95=0,sumLast=0,sumBytes=0,sumVerify=0;
  uint64_t totDataComp=0,totSig=0,totBoth=0,totRange=0;
  for(auto r:rxs){
    sumMed+=r->MedianAuth(); sumP95+=r->P95Auth();
    sumLast+=r->lastVerified; sumBytes+=r->rxBytes; sumVerify+=r->verifies;
    totDataComp+=r->dataComplete.size();
    totSig+=r->sigAvail.size();
    totBoth+=r->bothAuth.size();
    totRange+=r->blocksInRange();
  }
  double dur=sumLast/cfg.M;
  double verifyLoad=dur>0? (sumVerify/cfg.M)/dur:0;
  double cpuFrac=verifyLoad*cfg.verifyUs/1e6;
  double dataFrac=totRange? (double)totDataComp/totRange:0;
  double condFrac=totDataComp? (double)totBoth/totDataComp:0;
  double jointFrac=totRange? (double)totBoth/totRange:0;
  std::cout<<cfg.tag<<","<<cfg.mode<<","<<cfg.M<<","<<cfg.n<<","<<cfg.d
    <<","<<cfg.sigSize<<","<<cfg.loss<<","<<cfg.rttMs<<","<<cfg.lastRate
    <<","<<cfg.chunkC<<","<<cfg.fecR<<","<<cfg.ileave<<","<<cfg.burstLen
    <<","<<cfg.seed<<","<<(double)totRange/cfg.M
    <<","<<(double)totDataComp/cfg.M<<","<<(double)totSig/cfg.M
    <<","<<(double)totBoth/cfg.M
    <<","<<dataFrac<<","<<condFrac<<","<<jointFrac
    <<","<<sumBytes/cfg.M<<","<<sumVerify/cfg.M
    <<","<<sumMed/cfg.M<<","<<sumP95/cfg.M
    <<","<<verifyLoad<<","<<cpuFrac<<"\n";
  return 0;
}
