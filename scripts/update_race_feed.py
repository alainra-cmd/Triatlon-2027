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
 {"id":"fetri-2027-calendar","name":"FETRI · Calendario nacional e internacional 2027","country":"España","kind":"federation","url":"https://triatlon.org/noticias/fetri-lanza-el-calendario-de-competiciones-nacionales-e-internacionales-en-el-ano-2027/"},
 {"id":"andalucia","name":"Federación Andaluza","country":"España","kind":"regional","url":"https://triatlonandalucia.org/"},
 {"id":"aragon","name":"Federación Aragonesa · Competiciones","country":"España","kind":"regional","url":"https://www.triatlonaragon.org/Competiciones"},
 {"id":"asturias","name":"Federación Asturiana · Eventos","country":"España","kind":"regional","url":"https://triatlonasturias.es/events/"},
 {"id":"baleares","name":"Federació Balear","country":"España","kind":"regional","url":"https://fetrib.com/"},
 {"id":"canarias","name":"Federación Canaria","country":"España","kind":"regional","url":"https://www.fecantri.org/"},
 {"id":"cantabria","name":"Federación Cántabra","country":"España","kind":"regional","url":"https://fetricantabria.com/"},
 {"id":"clm","name":"Federación Castilla-La Mancha","country":"España","kind":"regional","url":"https://www.triatlonclm.org/"},
 {"id":"cyl","name":"Federación Castilla y León","country":"España","kind":"regional","url":"https://www.triatloncastillayleon.com/"},
 {"id":"cataluna","name":"Federació Catalana","country":"España","kind":"regional","url":"https://www.triatlo.org/competicions/?idany=2027&oficial=0"},
 {"id":"euskadi","name":"Euskadiko Triatloi Federazioa · Calendario","country":"España","kind":"regional","url":"https://triatloi.org/es/calendario/"},
 {"id":"extremadura","name":"Federación Extremeña","country":"España","kind":"regional","url":"https://triatlonextremadura.com/"},
 {"id":"galicia","name":"Federación Galega","country":"España","kind":"regional","url":"https://fegatri.org/"},
 {"id":"madrid","name":"Federación Madrileña · Calendario","country":"España","kind":"regional","url":"https://triatlonmadrid.org/competiciones/calendario/"},
 {"id":"murcia","name":"Federación de Murcia · Calendario provisional 2027 (PDF)","country":"España","kind":"regional","url":"https://trimurcia.es/wp-content/uploads/2026/10/Calendario-Provisional-FTRM-2027.pdf"},
 {"id":"navarra","name":"Federación Navarra","country":"España","kind":"regional","url":"https://www.navarratriatlon.com/"},
 {"id":"rioja","name":"Federación Riojana","country":"España","kind":"regional","url":"https://fertriatlon.com/"},
 {"id":"valencia","name":"Federació Comunitat Valenciana","country":"España","kind":"regional","url":"https://www.triatlocv.org/"},
 {"id":"ceuta","name":"Federación de Ceuta","country":"España","kind":"regional","url":"https://www.fetriceuta.org/"},
 {"id":"melilla","name":"Federación Melillense","country":"España","kind":"regional","url":"https://melillatriatlon.es/"},
 {"id":"portugal","name":"Federação de Triatlo de Portugal","country":"Portugal","kind":"federation","url":"https://www.federacao-triatlo.pt/"},
 {"id":"euskadi-entries","name":"Euskadi · Inscripciones federativas (RockTheSport)","country":"España","kind":"regional","url":"https://inscripciones.triatloi.org/es/events"},
 {"id":"ironman-europe","name":"IRONMAN · Europa (web oficial)","country":"Europe","kind":"franchise","url":"https://www.ironman.com/races"},
 {"id":"ironman-directory","name":"IRONMAN · Directorio europeo de contraste","country":"Europe","kind":"supplemental","url":"https://findmytris.com/races/continent/europe"},
 {"id":"challenge-europe","name":"Challenge Family · Europa","country":"Europe","kind":"franchise","url":"https://challengefamily.com/races/?_continent=europe"},
]
DATE_RE = re.compile(r"(20(?:26|27|28))[-/.](\d{1,2})[-/.](\d{1,2})|\b(\d{1,2})[./-](\d{1,2})[./-](20(?:26|27|28))\b")
MONTHS = {m.lower():i for i,m in enumerate(["","January","February","March","April","May","June","July","August","September","October","November","December"]) if m}
MONTHS.update({"ene":1,"enero":1,"jan":1,"feb":2,"febrero":2,"mar":3,"marzo":3,"abr":4,"abril":4,"apr":4,"may":5,"mayo":5,"jun":6,"junio":6,"jul":7,"julio":7,"ago":8,"agosto":8,"aug":8,"sep":9,"septiembre":9,"oct":10,"octubre":10,"nov":11,"noviembre":11,"dic":12,"diciembre":12,"dez":12,"fevereiro":2,"março":3,"maio":5,"junho":6,"julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12})
EUROPE = {"spain","portugal","france","germany","italy","austria","belgium","netherlands","luxembourg","switzerland","united kingdom","ireland","sweden","norway","denmark","finland","estonia","latvia","lithuania","poland","czechia","slovakia","slovenia","croatia","hungary","romania","bulgaria","greece","cyprus","malta","iceland","serbia","montenegro","bosnia","albania","turkey"}
SPORT = re.compile(r"triatl|duatl|acuatl|aquatl|swim.?run|multisport|ironman|challenge|triathlon|race", re.I)
LINK_WORDS = re.compile(r"calendar|calend|egutegi|compet|evento|event|race|prova|prueba|agenda|circuit|inscri", re.I)
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
 m=re.search(r"\b(\d{1,2})\s+(?:de\s+)?(January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|July|Jul|August|Aug|September|Sep|October|Oct|November|Nov|December|Dec|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|janeiro|fevereiro|março|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?2027\b",t,re.I)
 if m:
  mo=MONTHS.get(m.group(2).lower())
  if mo:return f"2027-{mo:02d}-{int(m.group(1)):02d}"
 m=re.search(r"\b(January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|July|Jul|August|Aug|September|Sep|October|Oct|November|Nov|December|Dec)\s+(\d{1,2}),?\s+2027\b",t,re.I)
 if m:
  mo=MONTHS.get(m.group(1).lower())
  if mo:return f"2027-{mo:02d}-{int(m.group(2)):02d}"
 return ""

def fetch(url):
 # Reintentos ante errores transitorios y esperas mayores para webs federativas lentas.
 last_error=None
 for attempt in range(3):
  try:
   r=session.get(url,timeout=(8,22),allow_redirects=True)
   r.raise_for_status()
   return r.url,r.headers.get("content-type","").lower(),r.content
  except requests.RequestException as exc:
   last_error=exc
   if attempt<2:time.sleep(1.5*(attempt+1))
 raise last_error

def infer_country(text):
 t=norm(text)
 countries={"espana":"Spain","españa":"Spain","spain":"Spain","portugal":"Portugal","francia":"France","france":"France","alemania":"Germany","germany":"Germany","italia":"Italy","italy":"Italy","austria":"Austria","belgica":"Belgium","belgium":"Belgium","paises bajos":"Netherlands","netherlands":"Netherlands","suiza":"Switzerland","switzerland":"Switzerland","reino unido":"United Kingdom","united kingdom":"United Kingdom","irlanda":"Ireland","ireland":"Ireland","suecia":"Sweden","sweden":"Sweden","noruega":"Norway","norway":"Norway","dinamarca":"Denmark","denmark":"Denmark","finlandia":"Finland","finland":"Finland","polonia":"Poland","poland":"Poland","chequia":"Czechia","czechia":"Czechia","eslovaquia":"Slovakia","slovakia":"Slovakia","eslovenia":"Slovenia","slovenia":"Slovenia","croacia":"Croatia","croatia":"Croatia","hungria":"Hungary","hungary":"Hungary","grecia":"Greece","greece":"Greece","estonia":"Estonia","letonia":"Latvia","lituania":"Lithuania","malta":"Malta","chipre":"Cyprus","islandia":"Iceland"}
 for key,value in countries.items():
  if key in t:return value
 return ""

def event_obj(name,date,place,source,url,kind="",country=None,dist=""):
 if not name or (not date and source["id"]!="challenge-europe"):return None
 if source["id"]=="ironman-europe" and (not country or norm(country) not in EUROPE):return None
 name=clean(name)[:180]
 if re.search(r"\b(curso|course|formacion|formación|training|clinic|webinar)\b",name,re.I):return None
 if not SPORT.search(name+" "+kind):return None
 if source["kind"]=="franchise" and source["id"]=="ironman-europe" and country and norm(country) not in EUROPE:return None
 return {"id":source["id"]+"-"+hashlib.sha1((norm(name)+date+norm(place)).encode("utf-8")).hexdigest()[:14],
 "name":name,"date":date,"place":clean(place)[:100] or "Localidad por confirmar",
 "country":country or source["country"],"type":"Duatlón" if re.search("duatl|duath",kind+" "+name,re.I) else ("Acuatlón" if re.search("aquatl",kind+" "+name,re.I) else "Triatlón"),
 "distance":clean(dist)[:80] or "Por confirmar","franchise":"IRONMAN" if source["id"].startswith("ironman-") else ("Challenge" if source["id"]=="challenge-europe" else ""),
 "url":url or source["url"],"sourceUrl":source["url"],"sourceName":source["name"],
 "dateStatus":"Fecha pendiente de confirmación" if not date else "Pendiente de verificar","availability":"Por verificar","status":"Extraída de calendario oficial; revisar cambios"}

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
    country={"ES":"Spain","PT":"Portugal","FR":"France","DE":"Germany","IT":"Italy","GB":"United Kingdom","NL":"Netherlands","BE":"Belgium","AT":"Austria","CH":"Switzerland","SE":"Sweden","NO":"Norway","DK":"Denmark","FI":"Finland","PL":"Poland"}.get(str(country).upper(),country)
    country=country or infer_country(place+" "+str(x.get("description","")))
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
   name_idx=next((i for i,h in enumerate(headers) if any(k in h for k in ["prova","prueba","evento","event","race","compet","nome","nom"])),None)
   place_idx=next((i for i,h in enumerate(headers) if any(k in h for k in ["local","cidade","city","lugar","location","poblac"])),None)
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

def extract_paragraphs(soup,source,page_url):
 out=[]
 for node in soup.find_all(["p","li"]):
  text=clean(node.get_text(" ",strip=True))
  if len(text)<18 or len(text)>420 or not SPORT.search(text):continue
  date=date_from(text)
  if not date:continue
  m=re.search(r"\b\d{1,2}\s+(?:de\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|janeiro|fevereiro|março|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?2027\b|\b(?:20)27[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[./-]\d{1,2}[./-]2027\b",text,re.I)
  if not m:continue
  before=text[:m.start()].strip(" ,;:·-")
  after=text[m.end():].strip(" ,;:·-")
  name=before if len(before)>5 and SPORT.search(before) else (after if len(after)>5 else text)
  if len(name)>150:name=name[:150]
  place=""
  pm=re.search(r"\b(?:en|in|em|at)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ'’ -]{2,35})",text)
  if pm:place=pm.group(1).strip()
  item=event_obj(name,date,place,source,page_url,text,infer_country(text))
  if item:out.append(item)
 return out

def parse_challenge_calendar(soup,source,page_url):
 out=[]
 headings=soup.find_all("h3")
 for node in headings:
  heading_text=clean(node.get_text(" ",strip=True))
  date=date_from(heading_text)
  pending_date=not date and bool(re.search(r"to be confirmed|\\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) 2027\\b",heading_text,re.I))
  if not date and not pending_date:continue
  prev=node.find_all_previous("h2",limit=2)
  if not prev:continue
  name=clean(prev[0].get_text(" ",strip=True))
  if name.lower()=="championship" and len(prev)>1 and clean(prev[1].get_text(" ",strip=True)).lower()=="the":
   name="The Championship"
  following=node.find_all_next("h3",limit=1)
  if not following:continue
  location=clean(following[0].get_text(" ",strip=True))
  distance_nodes=node.find_all_previous("h3",limit=1)
  distance=clean(distance_nodes[0].get_text(" ",strip=True)) if distance_nodes else ""
  if not re.search(r"100 distance|middle distance|long distance|standard distance|sprint distance|super sprint|aqua ?bike|triathlon|swim",distance,re.I):continue
  country=infer_country(location)
  if not country or norm(country) not in EUROPE:continue
  place=location.rsplit(",",1)[0].strip()
  item=event_obj(name,date,place,source,page_url,"Challenge Family triathlon",country,distance)
  if item:out.append(item)
 return out

def parse_ironman_directory(soup,source,page_url):
 out=[]
 for node in soup.find_all(["li","article"]):
  text=clean(node.get_text(" ",strip=True))
  if ("IRONMAN" not in text.upper() and "5150" not in text.upper()) or "2027" not in text:continue
  date=date_from(text)
  if not date:continue
  match=re.search(r"(?:—|-)\s*(?:January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|July|Jul|August|Aug|September|Sep|October|Oct|November|Nov|December|Dec)\s+\d{1,2},?\s+2027,?\s*(.+?)(?:\s*·\s*|$)",text,re.I)
  if not match:continue
  location=match.group(1).strip()
  parts=location.rsplit(",",1)
  if len(parts)!=2:continue
  place,country_text=parts[0].strip(),parts[1].strip()
  country=infer_country(country_text)
  if not country or norm(country) not in EUROPE:continue
  link=node.find("a",href=True)
  url=urljoin(page_url,link["href"]) if link else page_url
  dist="IRONMAN 70.3" if "70.3" in text else ("5150" if "5150" in text else "Larga distancia")
  name=clean(text.split("—",1)[0])
  item=event_obj(name,date,place,source,url,"IRONMAN triathlon",country,dist)
  if item:out.append(item)
 return out

def parse_murcia_2027(source):
 # Calendario provisional FTRM 2027 publicado en PDF oficial.
 records=[
  ("Duatlón por Equipos","2027-01-16","Archena","Duatlón"),
  ("Duatlón de Águilas · Clasificatorio y Regional","2027-01-24","Águilas","Duatlón"),
  ("Duatlón de Menores","2027-01-31","Alcantarilla","Duatlón"),
  ("Duatlón de Yecla","2027-02-14","Yecla","Duatlón"),
  ("Duatlón Calasparra","2027-02-21","Calasparra","Duatlón"),
  ("Duatlón de Lorca","2027-02-27","Lorca","Duatlón"),
  ("Duatlón Orihuela","2027-03-06","Orihuela","Duatlón"),
  ("Duatlón de Menores","2027-03-07","Caravaca de la Cruz","Duatlón"),
  ("Duatlón Torre Pacheco","2027-03-14","Torre Pacheco","Duatlón"),
  ("Triatlón San Pedro del Pinatar","2027-04-11","San Pedro del Pinatar","Triatlón"),
  ("Final Escolar de Duatlón","2027-04-24","San Pedro del Pinatar","Duatlón"),
  ("Triatlón Portman","2027-04-25","Portman (La Unión)","Triatlón"),
  ("Triatlón Orihuela","2027-05-09","Orihuela","Triatlón"),
  ("Triatlón de Águilas · Copa del Rey y C.E. Relevos","2027-05-15","Águilas","Triatlón"),
  ("Final Escolar de Triatlón","2027-05-22","Sede por determinar","Triatlón"),
  ("Triatlón Cartagena","2027-05-29","Cartagena","Triatlón"),
  ("Triatlón de Fuente Álamo · Clasificatorio y Regional","2027-06-05","Fuente Álamo","Triatlón"),
  ("Triatlón de Yecla","2027-06-20","Yecla","Triatlón"),
  ("Triatlón de Menores","2027-06-26","Alhama de Murcia","Triatlón"),
  ("Triatlón Blanca","2027-07-17","Blanca","Triatlón"),
  ("Acuatlón Alguazas","2027-09-04","Alguazas","Acuatlón"),
  ("Acuatlón Mazarrón","2027-09-12","Mazarrón","Acuatlón"),
  ("Acuatlón Santomera","2027-09-18","Santomera","Acuatlón"),
  ("Duatlón Cross La Unión","2027-10-24","La Unión","Duatlón"),
  ("Duatlón Cross Santomera","2027-11-07","Santomera","Duatlón")
 ]
 out=[]
 for name,date,place,kind in records:
  item=event_obj(name,date,place,source,source["url"],kind,"Spain")
  if item:
   item["notes"]="Calendario provisional FTRM 2027; sujeto a actualizaciones."
   out.append(item)
 return out

def parse_fetri_2027(source):
 records=[
  ("T100 Marbella 2027","2027-09-19","Marbella","Triatlón media distancia"),
  ("Copa del Mundo de Triatlón Lanzarote","2027-03-06","Lanzarote","Triatlón"),
  ("Copa del Mundo de Triatlón Tarragona","2027-04-10","Tarragona","Triatlón"),
  ("Copa del Mundo de Triatlón Melilla","2027-05-02","Melilla","Triatlón"),
  ("Campeonato de Europa de Duatlón Cáceres","2027-06-05","Cáceres","Duatlón"),
  ("Campeonato de Europa de Triatlón Sprint Ceuta","2027-10-02","Ceuta","Triatlón"),
  ("Campeonatos de Europa de Duatlón y Triatlón Cros Calahorra","2027-05-08","Calahorra","Duatlón y triatlón cros"),
  ("Copa de Europa de Triatlón Torremolinos","2027-04-24","Torremolinos","Triatlón"),
  ("Copa de Europa de Triatlón Tenerife","2027-10-10","Tenerife","Triatlón"),
  ("Campeonato de España de Triatlón Banyoles","2027-09-25","Banyoles","Triatlón"),
  ("Clasificatorio Campeonato de España de Triatlón Fuente Álamo","2027-06-05","Fuente Álamo","Triatlón"),
  ("Campeonato de España de Triatlón Cadete, Juvenil y Júnior Pontevedra","2027-06-26","Pontevedra","Triatlón"),
  ("Campeonato de España Escolar CESA CSD Tudela","2027-07-03","Tudela","Triatlón"),
  ("Campeonato de España de Acuatlón y Triatlón Cros Calahorra","2027-05-08","Calahorra","Acuatlón y triatlón"),
  ("Campeonato de España de Duatlón y Triatlón Gravel Vinuesa","2027-06-20","Vinuesa","Duatlón y triatlón"),
  ("Campeonatos de España de Triatlón por Clubes y Relevos Roquetas de Mar","2027-04-17","Roquetas de Mar","Triatlón"),
  ("Copa del Rey y Copa de la Reina de Triatlón Águilas","2027-05-15","Águilas","Triatlón"),
  ("Campeonato de España de Duatlón Avilés","2027-04-03","Avilés","Duatlón"),
  ("Campeonato de España de Duatlón Cadete, Juvenil y Júnior Huesca","2027-03-20","Huesca","Duatlón"),
  ("Campeonato de España de Duatlón Media Distancia Almazán","2027-02-14","Almazán","Duatlón"),
  ("Clasificatorio Duatlón de Carnavales Águilas","2027-01-24","Águilas","Duatlón"),
  ("Clasificatorio Duatlón Ólvega","2027-03-07","Ólvega","Duatlón"),
  ("Liga Nacional de Duatlón La Nucía","2027-01-30","La Nucía","Duatlón"),
  ("Liga Nacional de Duatlón Ciudad Real","2027-02-27","Ciudad Real","Duatlón"),
  ("Liga Nacional de Duatlón Albacete","2027-03-13","Albacete","Duatlón"),
  ("Campeonato de España de Swim Run Lanzarote","2027-05-29","Lanzarote","Swim Run"),
  ("Campeonato de España de Triatlón de Larga Distancia Doñana","2027-10-16","Matalascañas","Triatlón larga distancia"),
  ("Clasificatorio Campeonato de España de Triatlón Aguilar de Campoo","2027-06-12","Aguilar de Campoo","Triatlón")
 ]
 out=[]
 for name,date,place,kind in records:
  item=event_obj(name,date,place,source,source["url"],kind,"Spain")
  if item:out.append(item)
 return out

def candidate_links(soup,base,source):
 domain=urlparse(base).netloc.lower().removeprefix("www.")
 ranked={}
 for a in soup.find_all("a",href=True):
  href=urljoin(base,a["href"]).split("#")[0]
  p=urlparse(href)
  host=p.netloc.lower().removeprefix("www.")
  if p.scheme not in ("http","https") or not (host==domain or host.endswith("."+domain)):continue
  label=clean(a.get_text(" ",strip=True))
  combined=(href+" "+label).lower()
  if not LINK_WORDS.search(combined):continue
  score=0
  if re.search(r"calend|calendar|egutegi|competic|event|prova|prueba",label,re.I):score+=8
  if re.search(r"calend|calendar|egutegi|competic|event|prova|prueba",p.path,re.I):score+=6
  if re.search(r"2027|temporada|tempada",combined,re.I):score+=4
  if p.path.lower().endswith(".pdf"):score+=5
  if href not in ranked or score>ranked[href]:ranked[href]=score
 return [u for u,_ in sorted(ranked.items(),key=lambda item:(-item[1],item[0]))[:20]]

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
  failed_links=[]
  if "pdf" not in ctype and not body[:4]==b"%PDF":
   soup=BeautifulSoup(body,"html.parser")
   for link in candidate_links(soup,final,source)[:12]:
    try:
     u,ct,b=fetch(link);pages.append((u,ct,b));time.sleep(.2)
    except Exception as e:failed_links.append(urlparse(link).path+": "+str(e)[:90])
 except Exception as e:
  return [],{"id":source["id"],"name":source["name"],"status":"error","message":str(e)[:180],"pages":0,"events":0}
 found=[]
 for url,ct,body in pages:
  if "pdf" in ct or body[:4]==b"%PDF":found.extend(parse_pdf(body,source,url));continue
  soup=BeautifulSoup(body,"html.parser")
  if source["id"]=="challenge-europe":found.extend(parse_challenge_calendar(soup,source,url))
  elif source["id"]=="ironman-directory":found.extend(parse_ironman_directory(soup,source,url))
  else:
   found.extend(jsonld_events(soup,source,url))
   found.extend(extract_tables(soup,source,url))
   found.extend(extract_cards(soup,source,url))
   found.extend(extract_paragraphs(soup,source,url))
 if source["id"]=="fetri-2027-calendar":found.extend(parse_fetri_2027(source))
 if source["id"]=="murcia":found.extend(parse_murcia_2027(source))
 # Franchise pages are explicitly filtered to Europe by the provider's own region selection where available.
 if source["id"]=="challenge-europe":
  found=[x for x in found if norm(x.get("country","")) in EUROPE or x.get("country")=="Europe"]
 unique={}
 for x in found:
  k=(norm(x["name"]),x["date"],norm(x["place"]))
  unique[k]=x
 items=list(unique.values())
 message="Extracción completada" if items else "Se han consultado "+str(len(pages))+" páginas, pero no se han reconocido pruebas de 2027. Esto NO confirma que la federación carezca de calendario; requiere revisión."
 if failed_links:message+=" Enlaces secundarios fallidos: "+"; ".join(failed_links[:3])
 return items,{"id":source["id"],"name":source["name"],"status":"ok" if items else "needs_review","message":message,"pages":len(pages),"events":len(items),"failedLinks":len(failed_links)}

def discover_related_pages():
 # Búsqueda diaria complementaria en motores y páginas de organizadores,
 # clubes, circuitos y portales especializados. Solo acepta eventos de 2027.
 queries=[
  "triatlon 2027 calendario pruebas España Portugal",
  "duatlon acuatlon 2027 calendario pruebas España",
  "triathlon 2027 race calendar Spain Portugal",
  "provas triatlo 2027 calendario Portugal",
  "inscripciones triatlon 2027 España pruebas"
 ]
 results=[];seen=set();search_errors=[]
 for query in queries:
  try:
   endpoint="https://www.bing.com/search?format=rss&q="+requests.utils.quote(query)
   _,_,body=fetch(endpoint)
   rss=BeautifulSoup(body,"xml")
   for item in rss.find_all("item"):
    node=item.find("link")
    link=clean(node.get_text() if node else "")
    if not link:continue
    p=urlparse(link)
    if p.scheme not in ("http","https") or not p.netloc:continue
    link=link.split("#")[0]
    if link not in seen:
     seen.add(link);results.append((link,query))
  except Exception as exc:
   search_errors.append(str(exc)[:120])
 discovered=[]
 for url,query in results[:15]:
  source={"id":"web-discovery","name":"Búsqueda web diaria · "+urlparse(url).netloc,"country":"Europe","kind":"supplemental","url":url}
  items,report=scan_source(source)
  for event in items:
   event["sourceName"]="Búsqueda web diaria · "+urlparse(url).netloc
   event["status"]="Detectada en página relacionada; pendiente de verificación"
   event["notes"]="Hallazgo de búsqueda complementaria. Verificar fecha, organización e inscripción en la fuente enlazada."
  discovered.extend(items)
  print("web-discovery",url,report["status"],report["events"])
  time.sleep(.25)
 report={"id":"web-discovery","name":"Búsqueda diaria en páginas relacionadas con triatlón","status":"ok" if results and not search_errors else ("partial" if results else "error"),"message":str(len(queries))+" consultas; "+str(len(results))+" páginas candidatas; "+str(len(discovered))+" eventos detectados."+((" Errores: "+"; ".join(search_errors[:2])) if search_errors else ""),"pages":min(len(results),15),"events":len(discovered),"failedLinks":len(search_errors)}
 return discovered,report

def main():
 all_events=[];reports=[]
 for source in SOURCES:
  items,report=scan_source(source);all_events.extend(items);reports.append(report)
  print(source["id"],report["status"],report["events"])
  time.sleep(.4)
 discovered,discovery_report=discover_related_pages()
 all_events.extend(discovered);reports.append(discovery_report)
 print(discovery_report["id"],discovery_report["status"],discovery_report["events"])
 unique={}
 for e in all_events:
  k=(norm(e["name"]),e["date"],norm(e["place"]))
  if k not in unique:unique[k]=e
 payload={"generatedAt":datetime.now(timezone.utc).isoformat(),"season":YEAR,"sourceCount":len(reports),
 "successfulSources":sum(x["status"]=="ok" for x in reports),"failedSources":sum(x["status"]=="error" for x in reports),
 "events":sorted(unique.values(),key=lambda x:(x["date"],x["name"])),"sources":reports}
 with open("race-feed.json","w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False,indent=2)
 print("TOTAL",len(payload["events"]),"events; sources",len(reports))

if __name__=="__main__":main()
