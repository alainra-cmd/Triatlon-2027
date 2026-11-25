#!/usr/bin/env python3
"""Build a verifiable race feed from official triathlon federation and franchise calendars."""
import json, re, time, unicodedata, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

YEAR = 2027
HEADERS = {"User-Agent": "Triatlon2027CalendarBot/1.0 (+https://github.com/alainra-cmd/Triatlon-2027)"}
SOURCES = [
 {"id":"fetri","name":"FETRI · España","country":"España","kind":"federation","url":"https://triatlon.org/"},
 {"id":"andalucia","name":"Federación Andaluza","country":"España","kind":"regional","url":"https://triatlonandalucia.org/"},
 {"id":"aragon","name":"Federación Aragonesa","country":"España","kind":"regional","url":"https://www.triatlonaragon.org/"},
 {"id":"asturias","name":"Federación Asturiana","country":"España","kind":"regional","url":"https://triatlonasturias.es/"},
 {"id":"baleares","name":"Federació Balear","country":"España","kind":"regional","url":"https://fetrib.com/"},
 {"id":"canarias","name":"Federación Canaria","country":"España","kind":"regional","url":"https://www.fecantri.org/"},
 {"id":"cantabria","name":"Federación Cántabra","country":"España","kind":"regional","url":"https://fetricantabria.com/"},
 {"id":"clm","name":"Federación Castilla-La Mancha","country":"España","kind":"regional","url":"https://www.triatlonclm.org/"},
 {"id":"cyl","name":"Federación Castilla y León","country":"España","kind":"regional","url":"https://www.triatloncastillayleon.com/"},
 {"id":"cataluna","name":"Federació Catalana","country":"España","kind":"regional","url":"https://www.triatlo.org/"},
 {"id":"euskadi","name":"Euskadiko Triatloi Federazioa","country":"España","kind":"regional","url":"https://triatloi.org/es/"},
 {"id":"extremadura","name":"Federación Extremeña","country":"España","kind":"regional","url":"https://triatlonextremadura.com/"},
 {"id":"galicia","name":"Federación Galega","country":"España","kind":"regional","url":"https://fegatri.org/"},
 {"id":"madrid","name":"Federación Madrileña","country":"España","kind":"regional","url":"https://triatlonmadrid.org/"},
 {"id":"murcia","name":"Federación de Murcia","country":"España","kind":"regional","url":"https://trimurcia.es/"},
 {"id":"navarra","name":"Federación Navarra","country":"España","kind":"regional","url":"https://www.navarratriatlon.com/"},
 {"id":"rioja","name":"Federación Riojana","country":"España","kind":"regional","url":"https://fertriatlon.com/"},
 {"id":"valencia","name":"Federació Comunitat Valenciana","country":"España","kind":"regional","url":"https://www.triatlocv.org/"},
 {"id":"ceuta","name":"Federación de Ceuta","country":"España","kind":"regional","url":"https://fetriceuta.wixsite.com/fetriceuta"},
 {"id":"melilla","name":"Federación Melillense","country":"España","kind":"regional","url":"https://melillatriatlon.es/"},
 {"id":"portugal","name":"Federação de Triatlo de Portugal","country":"Portugal","kind":"federation","url":"https://www.federacao-triatlo.pt/"},
 {"id":"ironman-europe","name":"IRONMAN · Europa","country":"Europe","kind":"franchise","url":"https://www.ironman.com/races"},
 {"id":"challenge-europe","name":"Challenge Family · Europa","country":"Europe","kind":"franchise","url":"https://challengefamily.com/races/?_continent=europe"},
]
DATE_RE = re.compile(r"(20(?:26|27|28))[-/.](\d{1,2})[-/.](\d{1,2})|\b(\d{1,2})[./-](\d{1,2})[./-](20(?:26|27|28))\b")
MONTHS = {m.lower():i for i,m in enumerate(["","January","February","March","April","May","June","July","August","September","October","November","December"]) if m}
MONTHS.update({"ene":1,"enero":1,"jan":1,"feb":2,"febrero":2,"mar":3,"marzo":3,"abr":4,"abril":4,"apr":4,"may":5,"mayo":5,"jun":6,"junio":6,"jul":7,"julio":7,"ago":8,"agosto":8,"aug":8,"sep":9,"septiembre":9,"oct":10,"octubre":10,"nov":11,"noviembre":11,"dic":12,"diciembre":12,"dez":12,"fevereiro":2,"março":3,"maio":5,"junho":6,"julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12})
EUROPE = set("Spain Portugal France Germany Italy Austria Belgium Netherlands Luxembourg Switzerland United Kingdom Ireland Sweden Norway Denmark Finland Estonia Latvia Lithuania Poland Czechia Slovakia Slovenia Croatia Hungary Romania Bulgaria Greece Cyprus Malta Iceland Serbia Montenegro Bosnia Albania Turkey".lower().split())
SPORT = re.compile(r"triatl|duatl|aquatl|swim.?run|multisport|ironman|challenge|triathlon|race", re.I)
LINK_WORDS = re.compile(r"calendar|calend|compet|evento|event|race|prova|prueba|agenda|circuit|inscri", re.I)
session = requests.Session()
session.headers.update(HEADERS)

def clean(s):
 return re.sub(r"\s+"," ",BeautifulSoup(str(s or ""),"html.parser").get_text(" ",strip=True)).strip()

def norm(s):
 return "".join(c for c in unicodedata.normalize("NFD",str(s or "").lower()) if unicodedata.category(c)!="Mn")

def date_from(text):
 t=clean(text)
 m=DATE_RE.search(t)
 if m:
  if m.group(1):
   y,mo,day=map(int,m.group(1,2,3))
  else:
   day,mo,y=map(int,m.group(4,5,6))
  if y==YEAR and 1<=mo<=12 and 1<=day<=31:return f"{y:04d}-{mo:02d}-{day:02d}"
 # English/Spanish/Portuguese month-name dates
 m=re.search(r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|janeiro|fevereiro|março|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+2027\b",t,re.I)
 if m:
  mo=MONTHS.get(m.group(2).lower())
  if mo:return f"2027-{mo:02d}-{int(m.group(1)):02d}"
 return ""

def fetch(url):
 r=session.get(url,timeout=22,allow_redirects=True)
 r.raise_for_status()
 return r.url,r.headers.get("content-type","").lower(),r.content

def event_obj(name,date,place,source,url,kind="",country=None,dist=""):
 if not name or not date:return None
 name=clean(name)[:180]
 if not SPORT.search(name+" "+kind):return None
 if source["kind"]=="franchise" and source["id"]=="ironman-europe" and country and norm(country) not in EUROPE:return None
 return {"id":source["id"]+"-"+hashlib.sha1((norm(name)+date+norm(place)).encode("utf-8")).hexdigest()[:14],
 "name":name,"date":date,"place":clean(place)[:100] or "Localidad por confirmar",
 "country":country or source["country"],"type":"Duatlón" if re.search("duatl|duath",kind+" "+name,re.I) else ("Acuatlón" if re.search("aquatl",kind+" "+name,re.I) else "Triatlón"),
 "distance":clean(dist)[:80] or "Por confirmar","franchise":"IRONMAN" if source["id"]=="ironman-europe" else ("Challenge" if source["id"]=="challenge-europe" else ""),
 "url":url or source["url"],"sourceUrl":source["url"],"sourceName":source["name"],
 "dateStatus":"Pendiente de verificar","availability":"Por verificar","status":"Extraída de calendario oficial; revisar cambios"}

def jsonld_events(soup,source,page_url):
 out=[]
 for tag in soup.select('script[type="application/ld+json"]'):
  try:data=json.loads(tag.string or tag.get_text())
  except Exception:continue
  stack=data if isinstance(data,list) else [data]
  while stack:
   x=stack.pop()
   if isinstance(x,list):stack.extend(x);continue
   if not isinstance(x,dict):continue
   if "@graph" in x:stack.append(x["@graph"])
   typ=x.get("@type",[])
   if isinstance(typ,str):typ=[typ]
   if any("event" in str(t).lower() for t in typ):
    start=str(x.get("startDate",""))[:10]
    date=start if re.match(r"2027-\d\d-\d\d",start) else date_from(start)
    loc=x.get("location",{});addr=loc.get("address",{}) if isinstance(loc,dict) else {}
    place=loc.get("name","") if isinstance(loc,dict) else ""
    if isinstance(addr,dict):place=place or addr.get("addressLocality","")
    country=addr.get("addressCountry","") if isinstance(addr,dict) else ""
    out.append(event_obj(x.get("name"),date,place,source,x.get("url") or page_url,str(x.get("description","")),country))
   for v in x.values():
    if isinstance(v,(dict,list)):stack.append(v)
 return [x for x in out if x]

def extract_tables(soup,source,page_url):
 out=[]
 for table in soup.find_all("table"):
  rows=table.find_all("tr")
  if not rows:continue
  headers=[norm(clean(c)) for c in rows[0].find_all(["th","td"])]
  for row in rows[1:]:
   cells=row.find_all(["td","th"])
   if len(cells)<2:continue
   vals=[clean(c) for c in cells];whole=" | ".join(vals);date=date_from(whole)
   if not date:continue
   name_idx=next((i for i,h in enumerate(headers) if any(k in h for k in ["prova","prueba","evento","event","race","compet","nome"])),None)
   place_idx=next((i for i,h in enumerate(headers) if any(k in h for k in ["local","cidade","city","lugar","location"])),None)
   dist_idx=next((i for i,h in enumerate(headers) if "dist" in h),None)
   name=vals[name_idx] if name_idx is not None and name_idx<len(vals) else ""
   if not name:
    name=next((v for v in vals if SPORT.search(v) and len(v)>5),"")
   if not name:continue
   a=row.find("a",href=True);url=urljoin(page_url,a["href"]) if a else page_url
   place=vals[place_idx] if place_idx is not None and place_idx<len(vals) else ""
   kind=whole
   item=event_obj(name,date,place,source,url,kind,infer_country(whole),vals[dist_idx] if dist_idx is not None and dist_idx<len(vals) else "")
   if item:out.append(item)
 return out

def extract_cards(soup,source,page_url):
 out=[]
 selectors='article, [itemtype*="Event"], [class*="event"], [class*="race"], [class*="prova"], [class*="compet"]'
 for node in soup.select(selectors):
  text=clean(node.get_text(" ",strip=True))
  if len(text)<20 or len(text)>1800 or not SPORT.search(text):continue
  date=date_from(text)
  if not date:continue
  heading=node.find(["h1","h2","h3","h4"])
  name=clean(heading.get_text(" ",strip=True)) if heading else ""
  if not name:
   name=next((a.get_text(" ",strip=True) for a in node.find_all("a",href=True) if len(a.get_text(strip=True))>5), "")
  if not name:continue
  link=node.find("a",href=True);url=urljoin(page_url,link["href"]) if link else page_url
  place=""
  loc=node.select_one('[class*="location"],[class*="place"],[itemprop="location"]')
  if loc:place=clean(loc.get_text(" ",strip=True))
  item=event_obj(name,date,place,source,url,text,infer_country(text+" "+place))
  if item:out.append(item)
 return out

def candidate_links(soup,base,source):
 domain=urlparse(base).netloc
 found=[]
 for a in soup.find_all("a",href=True):
  href=urljoin(base,a["href"]).split("#")[0]
  p=urlparse(href)
  if p.scheme not in ("http","https") or p.netloc!=domain:continue
  if LINK_WORDS.search(href+" "+a.get_text(" ",strip=True)) and href not in found:found.append(href)
 return found[:12]

def parse_pdf(content,source,url):
 out=[]
 try:
  reader=PdfReader(BytesIO(content))
  for page in reader.pages:
   text=page.extract_text() or ""
   lines=[clean(x) for x in text.splitlines()]
   for i,line in enumerate(lines):
    date=date_from(line)
    if not date:continue
    context=" ".join(lines[max(0,i-1):min(len(lines),i+3)])
    if not SPORT.search(context):continue
    name=re.sub(DATE_RE,"",line).strip(" |·-")
    if len(name)<4:name=context[:150]
    out.append(event_obj(name,date,"",source,url,context))
 except Exception:pass
 return out

def scan_source(source):
 pages=[]
 try:
  final,ctype,body=fetch(source["url"])
  pages.append((final,ctype,body))
  if "pdf" not in ctype and not body[:4]==b"%PDF":
   soup=BeautifulSoup(body,"html.parser")
   for link in candidate_links(soup,final,source)[:8]:
    try:
     u,ct,b=fetch(link);pages.append((u,ct,b));time.sleep(.25)
    except Exception:pass
 except Exception as e:
  return [],{"id":source["id"],"name":source["name"],"status":"error","message":str(e)[:180],"pages":0,"events":0}
 found=[]
 for url,ct,body in pages:
  if "pdf" in ct or body[:4]==b"%PDF":found.extend(parse_pdf(body,source,url));continue
  soup=BeautifulSoup(body,"html.parser")
  found.extend(jsonld_events(soup,source,url))
  found.extend(extract_tables(soup,source,url))
  found.extend(extract_cards(soup,source,url))
 # Franchise pages are explicitly filtered to Europe by the provider's own region selection where available.
 if source["id"]=="challenge-europe":
  found=[x for x in found if norm(x.get("country","")) in EUROPE or x.get("country")=="Europe"]
 unique={}
 for x in found:
  k=(norm(x["name"]),x["date"],norm(x["place"]))
  unique[k]=x
 items=list(unique.values())
 return items,{"id":source["id"],"name":source["name"],"status":"ok" if items else "no_events_found","message":"Extracción completada" if items else "Página consultada; no se pudo reconocer un calendario estructurado","pages":len(pages),"events":len(items)}

def main():
 all_events=[];reports=[]
 for source in SOURCES:
  items,report=scan_source(source);all_events.extend(items);reports.append(report)
  print(source["id"],report["status"],report["events"])
  time.sleep(.4)
 unique={}
 for e in all_events:
  k=(norm(e["name"]),e["date"],norm(e["place"]))
  if k not in unique:unique[k]=e
 payload={"generatedAt":datetime.now(timezone.utc).isoformat(),"season":YEAR,"sourceCount":len(SOURCES),
 "successfulSources":sum(x["status"]=="ok" for x in reports),"failedSources":sum(x["status"]=="error" for x in reports),
 "events":sorted(unique.values(),key=lambda x:(x["date"],x["name"])),"sources":reports}
 with open("race-feed.json","w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False,indent=2)
 print("TOTAL",len(payload["events"]),"events; sources",len(reports))

if __name__=="__main__":main()
