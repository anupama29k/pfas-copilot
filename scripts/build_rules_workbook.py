import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation

D=dt.date
S={
 "ML":"https://www.morganlewis.com/pubs/2024/11/new-york-and-california-bans-on-pfas-in-textiles-and-apparel-begin-january-1-2025",
 "VEN":"https://www.mondaq.com/unitedstates/environmental-law/1525412/fashion-industry-bewarepfas-bans-on-apparel-effective-january-1-2025",
 "TS":"https://www.textileschool.com/42384/pfas-in-textiles-limits-dates-by-market/",
 "FOX":"https://pfas.foxrothschild.com/2026/09/state-regulation-of-pfas-in-the-fashion-industry-continues-to-evolve/",
 "MD":"https://www.manufacturingdive.com/news/pfas-forever-chemicals-state-laws-regulations-enacted-2026/808733/",
 "GK":"https://www.gklaw.com/Insights/Patchwork-of-State-PFAS-Regulations-Shaping-Product-Stewardship.htm",
 "WP":"https://blog.waveplm.com/pfas-in-clothing-what-fashion-brands/",
 "ML26":"https://www.morganlewis.com/pubs/2026/01/state-regulation-of-pfas-in-consumer-products-continues-to-gain-momentum-in-2026",
 "SBI":"https://sbifinishing.com/pfas-free-stain-protection-options/",
}
# id, jur, law, type, scope, exclusions/notes, basis, value, unit, test, date, severe_wet, duties, confidence, sources
R=[
("CA-1","California","AB 1817 (Health & Safety Code), 2022","Sales/manufacture ban","New textile articles: apparel, accessories, handbags, backpacks, bedding, towels, curtains, upholstery","Excludes PPE/professional uniforms, vehicle/vessel/aircraft textiles, filters, lab textiles, building fabric; severe-wet outdoor deferred to 2028","Intentionally added OR total organic fluorine",100,"ppm TOF","TOF (no standardized textile method; confirm lab method)",D(2025,1,1),"Deferred to 2028; must carry 'Made with PFAS chemicals' disclosure meanwhile","Certificate of compliance from manufacturer to sellers","High","ML; VEN"),
("CA-2","California","AB 1817","Threshold tightening","New textile articles: apparel, accessories, handbags, backpacks, bedding, towels, curtains, upholstery","Certificate duty applies at the lower level","Intentionally added OR total organic fluorine",50,"ppm TOF","TOF",D(2027,1,1),"n/a until 2028","Certificate of compliance","High","VEN; TS"),
("CA-3","California","AB 1817","Sales/manufacture ban","Outdoor apparel for severe wet conditions","End of deferral","Intentionally added OR total organic fluorine",50,"ppm TOF","TOF",D(2028,1,1),"Banned","Certificate of compliance","High","ML; TS"),
("CA-4","California","AB 347 (2024)","Registration","Textile producers/distributors selling into CA","DTSC to publish accepted test methods and lab accreditations; state enforcement from 2030","n/a",None,"","Per DTSC list (pending)",D(2029,7,1),"","Registration + statement of compliance with DTSC","Medium","TS; WP"),
("NY-1","New York","ECL §37-0121","Sales ban","New apparel (regular wear, formal, uniforms)","Severe-wet outdoor apparel exempt until 2028","Intentionally added",None,"","Supplier declarations / formulation records; targeted testing optional",D(2025,1,1),"Exempt until 2028","None specified","High","ML; VEN"),
("NY-2","New York","ECL §37-0121","Threshold (by regulation)","Apparel","DEC to set a PFAS level by regulation; date and level not yet fixed","Level set by DEC",None,"TBD","TBD",None,"","TBD","Low","TS"),
("NY-3","New York","ECL §37-0121","Sales ban","Outdoor apparel for severe wet conditions","","Intentionally added OR DEC level",None,"","",D(2028,1,1),"Banned","","High","ML; TS"),
("ME-1","Maine","38 MRSA §1614","Sales ban","Textile articles (clothing, bedding, upholstery) and upholstered furniture","Excludes severe-wet outdoor apparel and textiles used in vehicles, watercraft, aircraft","Intentionally added",None,"","",D(2026,1,1),"Excluded","","High","TS; MD"),
("ME-2","Maine","38 MRSA §1614","Disclosure","Outdoor apparel for severe wet conditions","Sources differ (disclosure vs ban); verify statute","Intentionally added",None,"","",D(2029,1,1),"Sale only with 'Made with PFAS chemicals' disclosure","Label disclosure","Medium","TS; WP"),
("ME-3","Maine","38 MRSA §1614","Sales ban (all products)","All products with intentionally added PFAS not already banned","Unless DEP rules the use currently unavoidable","Intentionally added",None,"","",D(2032,1,1),"Covered","","High","TS; SBI"),
("VT-1","Vermont","Act 54 (2024); AG guidance 2025","Manufacture/sales ban","Textiles and apparel","","Intentionally added OR total organic fluorine",100,"ppm TOF","TOF",D(2026,1,1),"Covered by general textile prohibition (per Fox Rothschild)","","Medium","TS; GK"),
("VT-2","Vermont","Act 54; AG guidance","Threshold tightening","Textiles and apparel","","Intentionally added OR total organic fluorine",50,"ppm TOF","TOF",D(2027,7,1),"","","Medium","TS; GK"),
("CT-1","Connecticut","Public Act 24-59","Disclosure","Outdoor apparel for severe wet conditions","","Intentionally added",None,"","",D(2026,1,1),"'Made with PFAS chemicals' disclosure","Label disclosure","Medium","FOX; WP"),
("CT-2","Connecticut","Public Act 24-59","Notification + labeling","Apparel, carpets/rugs, children's products, cosmetics, cookware, fabric treatments, textile furnishings, upholstered furniture, others","Manufacturer written notice to CT DEEP","Intentionally added",None,"","",D(2026,7,1),"","Visible label + written notice to DEEP","High","MD; GK"),
("CT-3","Connecticut","Public Act 24-59","Sales ban","Apparel and textile furnishings","Fox Rothschild lists a 2026 ban; 3 other sources say 2028. Verify","Intentionally added",None,"","",D(2028,1,1),"Banned","","Medium","TS; SBI; FOX"),
("CO-1","Colorado","SB 24-081 / PFAS Consumer Protection Act","Disclosure","Outdoor apparel for severe wet conditions","","Intentionally added",None,"","",D(2025,1,1),"Disclosure label","Label disclosure","Medium","FOX"),
("CO-2","Colorado","SB 24-081","Sales ban","Textile articles incl. apparel, accessories, backpacks, handbags; severe-wet outdoor apparel","","Intentionally added",None,"","",D(2028,1,1),"Banned","","High","TS; FOX"),
("WA-1","Washington","WAC 173-337-110 (Safer Products)","Manufacture/sales ban","Apparel and accessories","Footwear not in apparel definition","Intentionally added; total fluorine presumed intentional at/above",50,"ppm total F","Total fluorine (EN ISO 20999 style)",D(2027,1,1),"","","High","TS; FOX; ML26"),
("WA-2","Washington","Chapter 173-337 WAC","Reporting","Apparel, footwear and other textiles with intentionally added PFAS","Reports due Jan 2027","Intentionally added",None,"","",D(2026,1,1),"","Manufacturer reporting","Medium","FOX; SBI"),
("MN-1","Minnesota","Amara's Law (Minn. Stat. 116.943)","Sales ban","Fabric treatments, textile furnishings (not general apparel)","","Intentionally added",None,"","",D(2025,1,1),"","","High","TS"),
("MN-2","Minnesota","Amara's Law; PRISM reporting rule","Reporting","Products with intentionally added PFAS incl. apparel","Reporting system launched Jan 2026","Intentionally added",None,"","",D(2026,7,1),"","Manufacturer reporting + fees","Medium","FOX; SBI"),
("MN-3","Minnesota","Amara's Law","Sales ban (all products)","All products incl. apparel","Unless use designated currently unavoidable","Intentionally added",None,"","",D(2032,1,1),"Covered","","High","TS; SBI"),
("RI-1","Rhode Island","S 0220 and related acts","Disclosure + labeling","Outdoor apparel (disclosure); apparel (labeling)","Sources conflict on dates. Verify statute","Intentionally added",None,"","",D(2026,1,1),"Disclosure","Label disclosure","Low","FOX"),
("RI-2","Rhode Island","S 0220 and related acts","Sales ban","Apparel / textiles","Morgan Lewis (2024) said 2027; Fox Rothschild (2026) says 2028. Verify","Intentionally added",None,"","",D(2028,1,1),"","","Low","FOX; ML"),
("NM-1","New Mexico","PFAS Protection Act (2025)","Reporting + labeling","All products with intentionally added PFAS","Labeling preliminarily enjoined (litigation)","Intentionally added",None,"","",D(2027,1,1),"","Reporting; labeling enjoined","Medium","FOX"),
("EU-1","EU","Regulation (EU) 2024/2462 (PFHxA)","Restriction","Clothing, accessories, footwear, consumer mixtures","Per homogeneous material; 1,000 ppb for PFHxA-related substances","PFHxA and salts (targeted)",25,"ppb","EN 17681-1 (LC-MS/MS)",D(2026,10,10),"","","High","TS"),
("EU-2","EU","Regulation (EU) 2024/2462 (PFHxA)","Restriction","Home textiles: carpets, curtains, upholstery, bed linen, tablecloths","","PFHxA and salts (targeted)",25,"ppb","EN 17681-1 (LC-MS/MS)",D(2027,10,10),"","","High","TS"),
("EU-3","EU","POPs Regulation (PFOA)","Restriction","All articles","1 mg/kg for PFOA-related compounds","PFOA and salts (targeted)",25,"ppb","EN 17681-1",D(2020,7,4),"","","High","TS"),
("EU-4","EU","REACH Annex XVII entry 68 (C9-C14 PFCAs)","Restriction","All articles","260 ppb for related substances","C9-C14 PFCAs (targeted)",25,"ppb","EN 17681-1",D(2023,2,25),"","","High","TS"),
("EU-5","EU","Universal PFAS restriction (proposal)","Proposed restriction","Broad, with time-limited derogations","SEAC opinion expected end-2026; adoption years away","TBD",None,"","",None,"Interim derogations expected","","Medium","WP"),
("FR-1","France","Law 2025-188","Manufacture/import/sales ban","Consumer clothing, footwear, waterproofing agents","Protective and defence clothing exempt; recycled-content tolerance","Targeted single PFAS 25 ppb; sum 250 ppb; total F incl. polymers",50,"ppm total F","EN 17681-1 + EN ISO 20999",D(2026,1,1),"","","High","TS"),
("FR-2","France","Law 2025-188","Manufacture/import/sales ban","All textile products","Except essential uses, sovereignty uses, industrial technical textiles","As FR-1",50,"ppm total F","EN 17681-1 + EN ISO 20999",D(2030,1,1),"","","High","TS"),
("DK-1","Denmark","BEK nr 464 of 2025","Import/sales ban","Private-use clothing, footwear, waterproofing agents","Applies per component article","Total fluorine",50,"mg F/kg","EN ISO 20999 (combustion IC)",D(2026,7,1),"","","High","TS"),
]

wb=Workbook()
F="Arial"
hdr_font=Font(name=F,bold=True,color="FFFFFF"); hdr_fill=PatternFill("solid",fgColor="1F3A5F")
base=Font(name=F,size=10); thin=Side(style="thin",color="D0D0D0"); B=Border(top=thin,bottom=thin,left=thin,right=thin)
inp_font=Font(name=F,size=10,color="0000FF"); yellow=PatternFill("solid",fgColor="FFFF00")

# README
rd=wb.active; rd.title="README"
rows=[["PFAS Textile Rules Engine"],[],["How to use"],
["Reference date",D(2026,10,30)],
[],
["Rules sheet: one row per obligation. Status and Days-until columns are formulas driven by the reference date (yellow cell B4; type =TODAY() to make it live)."],
["Summary sheet: counts and next upcoming date per jurisdiction (formulas)."],
["Confidence: High = 2+ consistent sources; Medium = one detailed source or minor conflicts; Low = sources conflict. Low/Medium rows must be checked against the statute before use."],
["Not legal advice. Compiled from secondary sources (law-firm and industry trackers) as of 30 Oct 2026."],
["Scope codes (machine-readable, used by the copilot code): apparel, accessories, footwear, home_textiles, severe_wet, all. Limit kind: ban_intent, intent_or_tof, intent_or_total_f, total_f, targeted:<analyte>, obligation, tbd."],
["Example of adding a row: copy the last row of Rules, keep the Status/Days formulas, fill the blue columns."]]
for r in rows: rd.append(r)
rd["A1"].font=Font(name=F,bold=True,size=14); rd["A3"].font=Font(name=F,bold=True)
for c in ("A4",): rd[c].font=Font(name=F,bold=True)
rd["B4"].font=inp_font; rd["B4"].fill=yellow; rd["B4"].number_format="yyyy-mm-dd"
rd["B4"].comment=Comment("Input: date the Status column is evaluated against. Replace with =TODAY() for a live view.","Claude")
for r in range(6,11): rd.cell(r,1).font=base
rd.column_dimensions["A"].width=22; rd.column_dimensions["B"].width=14

# Rules
ws=wb.create_sheet("Rules")
CODES={'CA-1': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'CA-2': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'CA-3': ('severe_wet', 'intent_or_tof'), 'CA-4': ('apparel,accessories,home_textiles,severe_wet', 'obligation'), 'NY-1': ('apparel', 'ban_intent'), 'NY-2': ('apparel', 'tbd'), 'NY-3': ('severe_wet', 'ban_intent'), 'ME-1': ('apparel,accessories,home_textiles', 'ban_intent'), 'ME-2': ('severe_wet', 'obligation'), 'ME-3': ('all', 'ban_intent'), 'VT-1': ('apparel,accessories,home_textiles,severe_wet', 'intent_or_tof'), 'VT-2': ('apparel,accessories,home_textiles,severe_wet', 'intent_or_tof'), 'CT-1': ('severe_wet', 'obligation'), 'CT-2': ('apparel,home_textiles,severe_wet', 'obligation'), 'CT-3': ('apparel,home_textiles,severe_wet', 'ban_intent'), 'CO-1': ('severe_wet', 'obligation'), 'CO-2': ('apparel,accessories,home_textiles,severe_wet', 'ban_intent'), 'WA-1': ('apparel,accessories,severe_wet', 'intent_or_total_f'), 'WA-2': ('apparel,accessories,footwear,severe_wet', 'obligation'), 'MN-1': ('home_textiles', 'ban_intent'), 'MN-2': ('all', 'obligation'), 'MN-3': ('all', 'ban_intent'), 'RI-1': ('apparel,severe_wet', 'obligation'), 'RI-2': ('apparel', 'ban_intent'), 'NM-1': ('all', 'obligation'), 'EU-1': ('apparel,accessories,footwear,severe_wet', 'targeted:PFHxA'), 'EU-2': ('home_textiles', 'targeted:PFHxA'), 'EU-3': ('all', 'targeted:PFOA'), 'EU-4': ('all', 'targeted:C9-C14 PFCAs'), 'EU-5': ('all', 'tbd'), 'FR-1': ('apparel,footwear,severe_wet', 'total_f'), 'FR-2': ('apparel,accessories,footwear,home_textiles,severe_wet', 'total_f'), 'DK-1': ('apparel,footwear,severe_wet', 'total_f')}
H=["Rule ID","Jurisdiction","Law / citation","Rule type","Products covered","Exclusions / notes","Limit basis","Limit value","Limit unit","Test basis","Effective date","Severe-wet outdoor apparel","Duties (certificate / label / report)","Confidence","Sources","Status","Days until effective","Scope codes","Limit kind"]
ws.append(H)
for i,r in enumerate(R,start=2):
    ws.append(list(r))
    ws.cell(i,16).value=f'=IF(K{i}="","Not set / proposal",IF(K{i}<=README!$B$4,"In force","Upcoming"))'
    ws.cell(i,17).value=f'=IF(K{i}="","",MAX(0,K{i}-README!$B$4))'
    ws.cell(i,18).value=CODES[r[0]][0]; ws.cell(i,19).value=CODES[r[0]][1]
    ws.cell(i,11).number_format="yyyy-mm-dd"; ws.cell(i,17).number_format="0"
    for c in range(1,20):
        cell=ws.cell(i,c); cell.font=inp_font if (c<=15 or c>=18) else base; cell.border=B
        cell.alignment=Alignment(wrap_text=True,vertical="top")
for c in range(1,20):
    h=ws.cell(1,c); h.font=hdr_font; h.fill=hdr_fill; h.alignment=Alignment(wrap_text=True,vertical="center"); h.border=B
W=[8,13,26,18,36,36,26,9,11,24,12,26,26,11,14,16,10,30,18]
for i,w in enumerate(W,1): ws.column_dimensions[get_column_letter(i)].width=w
ws.freeze_panes="C2"; ws.auto_filter.ref=f"A1:S{len(R)+1}"
conf_fill={"High":"E5F4E4","Medium":"F9EEDA","Low":"FBEBEB"}
for i,r in enumerate(R,start=2): ws.cell(i,14).fill=PatternFill("solid",fgColor=conf_fill[r[13]])
dv=DataValidation(type="list",formula1='"High,Medium,Low"',allow_blank=True); ws.add_data_validation(dv); dv.add(f"N2:N500")

# Summary
sm=wb.create_sheet("Summary")
sm.append(["Jurisdiction","Rules tracked","In force","Upcoming","Next upcoming date","Low/Medium confidence rows"])
jur=[]
for r in R:
    if r[1] not in jur: jur.append(r[1])
n=len(R)+1
for j,name in enumerate(jur,start=2):
    sm.cell(j,1,name)
    sm.cell(j,2,f'=COUNTIF(Rules!$B$2:$B${n},A{j})')
    sm.cell(j,3,f'=COUNTIFS(Rules!$B$2:$B${n},A{j},Rules!$P$2:$P${n},"In force")')
    sm.cell(j,4,f'=COUNTIFS(Rules!$B$2:$B${n},A{j},Rules!$P$2:$P${n},"Upcoming")')
    sm.cell(j,5,f'=IF(D{j}=0,"—",_xlfn.MINIFS(Rules!$K$2:$K${n},Rules!$B$2:$B${n},A{j},Rules!$P$2:$P${n},"Upcoming"))')
    sm.cell(j,5).number_format="yyyy-mm-dd"
    sm.cell(j,6,f'=COUNTIFS(Rules!$B$2:$B${n},A{j},Rules!$N$2:$N${n},"Low")+COUNTIFS(Rules!$B$2:$B${n},A{j},Rules!$N$2:$N${n},"Medium")')
t=len(jur)+2
sm.cell(t,1,"Total").font=Font(name=F,bold=True)
for c in "BCDF": sm[f"{c}{t}"]=f"=SUM({c}2:{c}{t-1})"
for row in sm.iter_rows(min_row=2,max_row=t):
    for cell in row:
        cell.border=B
        if cell.font!=Font(name=F,bold=True): cell.font=base
for c in range(1,7):
    h=sm.cell(1,c); h.font=hdr_font; h.fill=hdr_fill; h.alignment=Alignment(wrap_text=True)
for i,w in enumerate([16,12,10,10,18,16],1): sm.column_dimensions[get_column_letter(i)].width=w

# Test methods
tm=wb.create_sheet("Test methods")
tm.append(["Method","What it measures","Typical use","Indicative cost per sample (USD)","Notes"])
TM=[("Total organic fluorine (TOF)","Organic fluorine only (TF minus inorganic F)","CA and VT ppm thresholds","A few hundred","No standardized textile TOF method yet; confirm the lab's method"),
("Total fluorine (TF), combustion IC — EN ISO 20999 / EN 14582 / ASTM D7359","All fluorine, organic + inorganic","WA 50 ppm presumption, Denmark, France 50 ppm","A few hundred","Can overestimate PFAS due to inorganic F"),
("Targeted PFAS, LC-MS/MS — EN 17681-1:2025","Specific listed PFAS (e.g. PFOA, PFHxA) at ppb","EU restrictions, France single/sum limits, confirming a TOF hit","400–700","Misses PFAS not on the target list"),
("EN 17681-2","Volatile PFAS (e.g. FTOHs)","Complement to 17681-1","Not stated",""),
("ZDHC MRSL","Chemical list, not a test","Supplier chemical declarations","n/a","")]
for r in TM: tm.append(list(r))
for row in tm.iter_rows():
    for cell in row: cell.font=base; cell.alignment=Alignment(wrap_text=True,vertical="top"); cell.border=B
for c in range(1,6):
    h=tm.cell(1,c); h.font=hdr_font; h.fill=hdr_fill
for i,w in enumerate([40,34,36,18,40],1): tm.column_dimensions[get_column_letter(i)].width=w
tm.cell(len(TM)+3,1,"Cost source: HQTS, All you need to know about PFAS testing — https://www.hqts.com/?p=183995").font=base

# Sources
so=wb.create_sheet("Sources")
TITLES={'ML': 'Morgan Lewis (2024): New York and California bans on PFAS in textiles and apparel', 'VEN': 'Venable via Mondaq (2024): Fashion industry beware — PFAS bans on apparel', 'TS': 'Textile School: PFAS in textiles — limits, dates and test methods by market', 'FOX': 'Fox Rothschild (Sept 2026): State regulation of PFAS in the fashion industry', 'MD': 'Manufacturing Dive (2026): State PFAS laws taking effect in 2026', 'GK': 'Godfrey & Kahn: Patchwork of state PFAS regulations', 'WP': 'WavePLM (2026): PFAS in clothing — what brands must test, disclose and fix', 'ML26': 'Morgan Lewis (Jan 2026): State regulation of PFAS in consumer products in 2026', 'SBI': 'SBI Finishing: PFAS-free stain protection and 2026 state bans'}
so.append(["Key","URL","Title"])
for k,u in S.items(): so.append([k,u,TITLES.get(k,"")])
for row in so.iter_rows():
    for cell in row: cell.font=base
for c in (1,2,3): so.cell(1,c).font=hdr_font; so.cell(1,c).fill=hdr_fill
so.column_dimensions["C"].width=80
so.column_dimensions["A"].width=8; so.column_dimensions["B"].width=110

import sys; wb.save(sys.argv[1] if len(sys.argv) > 1 else "rules.xlsx")
print(len(R),"rules")
