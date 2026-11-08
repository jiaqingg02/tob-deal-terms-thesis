"""Functions that cut the passages for each deal term out of the two disclosure documents.

The functions are copied without change from the programs that made the passages read by the earlier
generative-AI judgments (fill_summary/cut_sections.py, fill_summary/iken/cut_iken.py, fill_summary/cut_old.py),
so that the passages used by the rules are exactly the same. Only the file reading is moved to
00_cut_document_passages.py. Names of the target and the acquirer and the securities code are replaced by "■■".

  THEMES  7 passages of the tender offer registration statement (or the announcement of the start of the offer):
          price, rival, board, shareholder, funding, regulatory, structure
  TH      4 passages of the opinion statement: committee, policy, valuation, mom
"""
import re
import unicodedata

def clean(t):
    t=unicodedata.normalize('NFKC',t)
    t=re.sub(r'EDINET提出書類\s*\S{0,60}?\(E\d{5}\)\s*(公開買付届出書|意見表明報告書)\s*(\d+/\d+)?','',t)
    return re.sub(r'\s+','',t)
def names(t):
    out=set()
    for pat in [r'「(?:対象者|当社)」とは、(.{2,40}?)をいい',r'「公開買付者」とは、(.{2,40}?)をいい',r'【届出者の氏名又は名称】(.{2,40}?)【',r'【報告者の名称】(.{2,40}?)【']:
        for m in re.finditer(pat,t[:20000]):
            n=m.group(1)
            for x in re.split(r'(?:及び|並びに|、)',n):
                x=x.strip('()（）')
                core=re.sub(r'(株式会社|合同会社|有限会社|\(株\)|ホールディングス|HD)','',x)
                if len(x)>=2: out.add(x)
                if len(core)>=2: out.add(core)
    return sorted(out,key=len,reverse=True)
def mask(t,ns,code):
    for n in ns: t=t.replace(n,'■■')
    return t.replace(code,'■■')
def win(t,pats,w=250,cap=3000,need=None,skip=None):
    sp=[]
    for p in pats:
        for m in re.finditer(p,t):
            a,b=max(0,m.start()-w),min(len(t),m.end()+w)
            if need and need not in t[a:b]: continue
            if skip and any(skip_a<=m.start()<skip_b for skip_a,skip_b in skip): continue
            sp.append((a,b))
    sp.sort(); mg=[]
    for a,b in sp:
        if mg and a<=mg[-1][1]: mg[-1]=(mg[-1][0],max(mg[-1][1],b))
        else: mg.append((a,b))
    out='';
    for a,b in mg:
        if len(out)>=cap: break
        out+='…'+t[a:b][:cap-len(out)]+'…\n'
    return out
def head(t,pats,n=2000):
    for p in pats:
        ms=list(re.finditer(p,t))
        if ms: m=ms[-1] if len(ms)>1 else ms[0]; return t[m.start():m.start()+n]+'…\n'
    return ''
def dedup_add(base,extra):
    # extra 里已经出现在 base 中的片段不再重复
    keep=[c for c in extra.split('…\n') if c.strip('…') and c.strip('…')[len(c.strip('…'))//2-30:len(c.strip('…'))//2+30] not in base]
    return '…\n'.join(keep)+('…\n' if keep else '')
def sh(T):
    a=head(T,[r'重要な合意に関する事項'],2500)+win(T,[r'応募契約',r'不応募',r'応募する旨',r'応募しない旨',r'応募合意'],250,2500)
    b=dedup_add(a,win(T,[r'前提条件',r'解除',r'撤回することができ',r'撤回できる',r'対抗',r'上回る'],300,6000,need='応募'))
    return a+'【応募契約の前提条件・解除・撤回に関する記述】\n'+b[:4500]
THEMES={
 'price':(lambda T,I: (lambda a: a+win(I+T,[r'提案',r'交渉',r'本公開買付価格を'],250,max(0,6000-len(a))) if len(a)<3000 else a)(win(I+T,[r'再提案',r'提案価格',r'価格の引上げ',r'価格の引き上げ',r'引上げを要請',r'引き上げを要請',r'最終提案',r'応諾',r'価格交渉',r'十分な水準',r'不十分',r'1株当たり[0-9,]+円とする'],280,6000))),
 'rival':(lambda T,I: win(I+T,[r'対抗',r'競合',r'他の買収',r'マーケット・チェック',r'入札',r'複数の(?:候補|買収)',r'意向表明書',r'第三者からの(?:提案|買収)'],250,2500)),
 'board':(lambda T,I: (lambda S: head(S,[r'\(1\)意見の内容',r'意見の内容'],1500)+win(S,[r'賛同',r'推奨',r'中立',r'委ねる',r'留保',r'反対の意見'],200,2000))(I if I else T)),  # 没有意見表明報告書时用届出書
 'shareholder':(lambda T,I: sh(T)),
 'funding':(lambda T,I: head(T,[r'【買付け等に要する資金】',r'買付け等に要する資金'],2200)+win(T,[r'融資証明書',r'借入',r'出資証明書',r'自己資金'],200,1800)),
 'regulatory':(lambda T,I: head(T,[r'株券等の取得に関する許可等'],2200)+win(T,[r'公正取引委員会',r'外為法',r'外国為替',r'競争当局',r'認可',r'許可',r'承認'],200,2000)),
 'structure':(lambda T,I: head(T,[r'買付予定の株券等の数'],1200)+win(T,[r'上限',r'按分',r'上場を維持',r'上場維持',r'二段階',r'スクイーズアウト'],200,2000)),
}
JP={'price':'価格交渉','rival':'対抗提案・入札','board':'対象者取締役会の意見','shareholder':'大株主の応募・不応募の合意','funding':'買付資金','regulatory':'許認可・当局の手続','structure':'買付の構造（上限・下限・二段階）'}

def committee(I,T):
    S=I if I else T
    a=win(S,[r'旨の(?:本)?答申書',r'旨の答申を'],700,1800)
    st=[m.start() for m in re.finditer(r'(?:大要以下|以下の内容の(?:本)?答申|以下の(?:本)?答申)',S)]
    b=''
    if st:
        R=S[st[-1]:st[-1]+45000]
        nx=re.search(r'[0-9](?:当社|対象者)における(?:独立した)?(?:法律|第三者算定|ファイナンシャル|利害関係)',R[300:])
        if nx: R=R[:300+nx.start()]
        b=R[:1200]+'…\n'+win(R[1200:],[r'推奨',r'委ね',r'中立',r'不利益',r'妥当(?:である)?とは(?:いえ|言え)ない',r'付帯',r'留保'],250,3200)
    c=win(S,[r'独立役員',r'社外取締役.{0,30}意見(?:書|を入手)',r'利害関係を有しない(?:社外)?(?:取締役|監査役).{0,40}意見'],250,1000)
    return a+'【答申の内容（抜粋）】'+b+('\n【独立役員等の意見】'+c if c else '')
def dedup_add_s(base,extra):
    return extra if extra[200:260] not in base else ''
def policy(I,T):
    S=I+T
    return ('【上場】'+head(S,[r'上場廃止となる見込み及びその事由'],700)+win(S,[r'上場を維持',r'上場維持'],200,1200)
            +'【配当】'+win(S,[r'配当'],220,2200)+'【株主優待】'+win(S,[r'優待'],220,900)
            +'【公開買付け後の経営方針】'+head(S,[r'本公開買付け後の経営方針'],900))
def valuation(I,T):
    S=I if I else T
    a=head(S,[r'(?:当社|対象者)株式の1株当たりの株式価値の範囲',r'算定結果'],1500)
    b=win(S,[r'DCF法(?:では|による算定)?[:：]?\s*[0-9,]+円',r'類似(?:上場)?会社(?:比較|比準)法(?:では)?[:：]?\s*[0-9,]+円',r'市場株価(?:平均)?法(?:では)?[:：]?\s*[0-9,]+円',r'株式価値の範囲'],200,2200)
    c=head(T if T else S,[r'【買付け等の価格】',r'買付け等の価格'],500)
    return '【買付価格】'+c+'【算定結果】'+a+b
def mom(I,T):
    S=I+T
    return win(S,[r'マジョリティ・オブ・マイノリティ',r'Majority\s*of\s*Minority',r'MajorityofMinority'],350,1800)+'【買付予定数の下限】'+head(T if T else S,[r'買付予定数の下限'],600)
TH={'committee':(committee,'特別委員会の意見（少数株主の利益）'),'policy':(policy,'今後の方針（上場・配当・株主優待）'),'valuation':(valuation,'買付価格と株式価値の算定結果'),'mom':(mom,'マジョリティ・オブ・マイノリティ条件と買付予定数の下限')}

def names_old(T, I, extra):
    out = set(names(T) + names(I))
    for t in (T, I):
        for m in re.finditer(r'([^、。「」()（）\s]{2,40}?)(?:\((?:[^()]{0,120}?)\))?\(以下「(?:対象者|当社|当行|公開買付者|公開買付者ら|買付者|本応募合意株主|親会社)[^」]{0,10}」', t[:60000]):
            x = m.group(1)
            x = re.sub(r'^(?:である|は|が|の|、|及び|並びに)', '', x)
            if 2 <= len(x) <= 40 and not re.search(r'本公開買付け|株式|株券|取締役|年|月|日', x): out.add(x)
        for m in re.finditer(r'(?:公開買付者の概要|買付者の概要)[^。]{0,30}?名称(.{2,40}?)(?:\(2\)|所在地|②)', t):
            out.add(m.group(1))
    for x in extra:
        if x and len(x) >= 2: out.add(x)
    core = set()
    for x in out:
        c = re.sub(r'(株式会社|合同会社|有限会社|\(株\)|ホールディングス|HD)', '', x)
        if len(c) >= 2: core.add(c)
    return sorted(out | core, key=len, reverse=True)
