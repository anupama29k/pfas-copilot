import datetime
import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation

D=dt.date
S={'ML': 'https://www.morganlewis.com/pubs/2024/11/new-york-and-california-bans-on-pfas-in-textiles-and-apparel-begin-january-1-2025', 'VEN': 'https://www.mondaq.com/unitedstates/environmental-law/1525412/fashion-industry-bewarepfas-bans-on-apparel-effective-january-1-2025', 'TS': 'https://www.textileschool.com/42384/pfas-in-textiles-limits-dates-by-market/', 'FOX': 'https://pfas.foxrothschild.com/2026/09/state-regulation-of-pfas-in-the-fashion-industry-continues-to-evolve/', 'MD': 'https://www.manufacturingdive.com/news/pfas-forever-chemicals-state-laws-regulations-enacted-2026/808733/', 'GK': 'https://www.gklaw.com/Insights/Patchwork-of-State-PFAS-Regulations-Shaping-Product-Stewardship.htm', 'WP': 'https://blog.waveplm.com/pfas-in-clothing-what-fashion-brands/', 'ML26': 'https://www.morganlewis.com/pubs/2026/01/state-regulation-of-pfas-in-consumer-products-continues-to-gain-momentum-in-2026', 'SBI': 'https://sbifinishing.com/pfas-free-stain-protection-options/', 'CTG': 'https://prdext3.cga.ct.gov/2026/sup/chap_446z.htm', 'CTDEEP': 'https://portal.ct.gov/deep/p2/pfas-in-products', 'RIDEM': 'https://dem.ri.gov/pfas-products', 'RIBILL': 'https://webserver.rilegislature.gov/BillText24/HouseText24/H7356Aaa.htm', 'SGSRI': 'https://www.sgs.com/en-gb/news/2026/06/safeguards-09026-rhode-island-usa-revises-consumer-pfas-ban-act-of-2024', 'VTAG': 'https://ago.vermont.gov/sites/ago/files/Guidance%20on%20PFAS%20Product%20Bans%20%282025%29.pdf', 'VTACT': 'https://legislature.vermont.gov/Documents/2026/Docs/ACTS/ACT054/ACT054%20As%20Enacted.pdf', 'MESTAT': 'https://www.legislature.maine.gov/statutes/38/title38sec1614.pdf', 'MEDEP': 'https://www.maine.gov/dep/spills/topics/pfas/PFAS-products/index.html', 'DD347': 'https://calmatters.digitaldemocracy.org/bills/ca_202320240ab347', 'BCLP347': 'https://www.bclplaw.com/en-US/events-insights-news/pfas-update-california-enacts-new-pfas-enforcement-and-registration-law.html', 'KDCA': 'https://www.kelleydrye.com/viewpoints/client-advisories/preparing-for-californias-ban-on-pfas-in-textiles', 'COLEG': 'https://www.leg.colorado.gov/bills/SB24-081', 'BCLPCO': 'https://bclplaw.com/en-US/events-insights-news/colorado-increases-restrictions-on-pfas-in-consumer-products.html', 'BHFS': 'https://bhfs.com/insights/alerts-articles/2024/colorado-expands-pfas-labeling-and-phase-out-rules', 'WAORDER': 'https://ecology.wa.gov/getattachment/5d1caab2-16f7-49c5-a66a-4c3928c5ec3b/WSR-25-24-007.pdf', 'BVWA': 'https://www.cps.bureauveritas.com/newsroom/washington-state-finalizes-cycle-15-pfas-rule', 'EXPWA': 'https://www.exponent.com/article/washington-state-adopts-new-pfas-restrictions-and-reporting', 'FDMN': 'https://www.faegredrinker.com/en/insights/publications/2026/4/minnesota-pfas-reporting-deadline-extension-and-enhanced-support', 'MPCA': 'https://www.pca.state.mn.us/sites/default/files/20240725-presentation-pfas-prohibitions.pdf', 'NMHB': 'https://nmlegis.gov/Sessions/25%20Regular/final/HB0212.PDF', 'NMED': 'https://www.env.nm.gov/pfas/pfas-protection-act-hb212/', 'FDNM': 'https://www.faegredrinker.com/en/insights/publications/2026/9/federal-court-blocks-enforcement-of-labeling-provisions-of-new-mexico-pfas-protection-act', 'NYDEC': 'https://dec.ny.gov/environmental-protection/help-for-businesses/pfas-in-apparel-law', 'NHRSA': 'https://gc.nh.gov/rsa/html/X/149-M/149-M-64.htm'}
# id, jur, law, type, scope, exclusions/notes, basis, value, unit, test, date, severe_wet, duties, confidence, sources
R=[('CA-1', 'California', 'AB 1817 (Health & Safety Code §108970–108971)', 'Sales/manufacture ban', 'New textile articles: apparel, accessories, handbags, backpacks, bedding, towels, curtains, upholstery', 'Excludes PPE/professional uniforms, vehicle/vessel/aircraft textiles, filters, lab textiles, building fabric; severe-wet outdoor deferred to 2028', 'Intentionally added OR total organic fluorine ≥', 100, 'ppm TOF', 'TOF (no standardized textile method; confirm lab method)', datetime.date(2025, 1, 1), 'Deferred to 2028 (see CA-6 disclosure)', 'Signed certificate of compliance from manufacturer to sellers; use least toxic alternative', 'High', 'ML; VEN; KDCA'),
('CA-2', 'California', 'AB 1817', 'Threshold tightening', 'New textile articles: apparel, accessories, handbags, backpacks, bedding, towels, curtains, upholstery', 'Certificate duty applies at the lower level', 'Intentionally added OR total organic fluorine ≥', 50, 'ppm TOF', 'TOF', datetime.date(2027, 1, 1), 'n/a until 2028', 'Certificate of compliance', 'High', 'VEN; TS; KDCA'),
('CA-3', 'California', 'AB 1817', 'Sales/manufacture ban', 'Outdoor apparel for severe wet conditions', 'End of deferral', 'Intentionally added OR total organic fluorine ≥', 50, 'ppm TOF', 'TOF', datetime.date(2028, 1, 1), 'Banned', 'Certificate of compliance', 'High', 'ML; TS; KDCA'),
('CA-6', 'California', 'AB 1817', 'Disclosure', 'Outdoor apparel for severe wet conditions', 'Applies until the 2028 ban (CA-3)', 'Intentionally added PFAS', None, '', '', datetime.date(2025, 1, 1), "'Made with PFAS chemicals' disclosure, including online listings", 'Label disclosure incl. online', 'High', 'ML; KDCA'),
('CA-4', 'California', 'AB 347 (Ch. 932, Stats. 2024), §108079', 'Registration', 'Textile articles (also juvenile products, food packaging)', 'DTSC must adopt regulations and publish accepted test methods and lab accreditations by 2029-01-01; DTSC duties depend on funding', 'n/a', None, '', 'Per DTSC list (due 2029-01-01)', datetime.date(2029, 7, 1), '', 'Register, pay fee, file statement of compliance per covered product; technical documentation on request', 'High', 'DD347; BCLP347'),
('CA-5', 'California', 'AB 347, §108079(d)', 'Enforcement start', 'Textile articles', 'DTSC enforcement; penalties not less than $10,000 for a first violation, daily for continuing violations', 'n/a', None, '', '', datetime.date(2030, 7, 1), '', 'Subject to DTSC notices of violation and penalties', 'High', 'DD347; BCLP347'),
('NY-1', 'New York', 'ECL §37-0121', 'Sales ban', 'New apparel (regular wear, formal, uniforms)', 'Severe-wet outdoor apparel exempt until 2028; retailers should obtain manufacturer certificates', 'Intentionally added', None, '', 'Supplier declarations / formulation records', datetime.date(2025, 1, 1), 'Exempt until 2028', 'Manufacturer certificates to retailers (recommended)', 'High', 'ML; VEN; NYDEC'),
('NY-2', 'New York', 'ECL §37-0121', 'Threshold (by regulation)', 'Apparel', 'DEC considering 50 ppm TOF and 25–1,000 ppb individual PFAS; no level set as of Oct 2026', 'Level set by DEC', None, 'TBD', 'TBD', None, '', 'TBD', 'Medium', 'NYDEC'),
('NY-3', 'New York', 'ECL §37-0121', 'Sales ban', 'Outdoor apparel for severe wet conditions', 'DEC proposes to exclude merely water-resistant outerwear', 'Intentionally added OR DEC level (not yet set)', None, '', '', datetime.date(2028, 1, 1), 'Banned', '', 'High', 'ML; NYDEC'),
('ME-1', 'Maine', '38 M.R.S. §1614(5)(B-1)', 'Sales ban', 'Textile articles (apparel, accessories, handbags, backpacks, draperies) and upholstered furniture', 'Excludes severe-wet outdoor apparel, vehicle/watercraft/aircraft textiles, PPE (per DEP); continued sale only with a currently-unavoidable-use determination', 'Intentionally added', None, '', '', datetime.date(2026, 1, 1), 'Excluded', 'CUU notification only where a CUU applies (firms ≤100 employees exempt)', 'High', 'MESTAT; MEDEP'),
('ME-2', 'Maine', '38 M.R.S. §1614(5)(B-2)(2)', 'Ban with disclosure exception', 'Outdoor apparel for severe wet conditions', 'No disclosure duty before 2029', 'Intentionally added', None, '', '', datetime.date(2029, 1, 1), "Sale only with 'Made with PFAS chemicals' disclosure, incl. online", 'Label disclosure incl. online', 'High', 'MESTAT; MEDEP'),
('ME-3', 'Maine', '38 M.R.S. §1614', 'Sales ban (all products)', 'All products with intentionally added PFAS not already banned', 'Unless DEP rules the use currently unavoidable', 'Intentionally added', None, '', '', datetime.date(2032, 1, 1), 'Covered', '', 'High', 'MESTAT; TS'),
('VT-1', 'Vermont', 'Act 54 (2025); 9 V.S.A. §2494f', 'Sales ban', 'Textiles and textile articles incl. apparel', 'Excludes severe-wet outdoor apparel, PPE and military-only clothing until 2028-07-01', 'Intentionally added OR total organic fluorine ≥', 100, 'ppm TOF', 'TOF', datetime.date(2026, 1, 1), 'Excluded until 2028-07-01 (VT-3)', 'Certificate of compliance on Attorney General request (§2494h)', 'High', 'VTAG; VTACT'),
('VT-2', 'Vermont', 'Act 54 (2025), Sec. 2', 'Threshold tightening', 'Textiles and textile articles incl. apparel', "New 'intentionally added' definition also takes effect", 'Intentionally added OR total organic fluorine ≥', 50, 'ppm TOF', 'TOF', datetime.date(2027, 7, 1), 'Excluded until 2028-07-01', 'Certificate on request', 'High', 'VTAG; VTACT'),
('VT-3', 'Vermont', 'Act 54 (2025), Sec. 3, 13(d)', 'Sales ban', 'Outdoor apparel for severe wet conditions', '', 'Intentionally added OR total organic fluorine ≥', 50, 'ppm TOF', 'TOF', datetime.date(2028, 7, 1), 'Banned', 'Certificate on request', 'High', 'VTAG; VTACT'),
('CT-1', 'Connecticut', 'Conn. Gen. Stat. §22a-903c(c)(1) (PA 24-59)', 'Disclosure', 'Outdoor apparel for severe wet conditions', 'Applies 2026-01-01 to 2027-12-31; replaced by the 2028 ban (CT-3)', 'Intentionally added', None, '', '', datetime.date(2026, 1, 1), "'Made with PFAS chemicals' disclosure, incl. online listings", 'Label disclosure incl. online', 'High', 'CTG; CTDEEP'),
('CT-2', 'Connecticut', 'Conn. Gen. Stat. §22a-903c(b)-(c)', 'Notification + labeling', 'Apparel, carpets/rugs, cleaning products, cookware, cosmetics, fabric treatments, juvenile products, textile furnishings, upholstered furniture, others', 'Prior written notice to DEEP ($800 fee per DEEP); DEEP-approved label visible before sale', 'Intentionally added', None, '', '', datetime.date(2026, 7, 1), '', 'Written notice to DEEP + DEEP-approved label', 'High', 'CTG; CTDEEP'),
('CT-3', 'Connecticut', 'Conn. Gen. Stat. §22a-903c(d)', 'Sales ban', 'Apparel, textile furnishings, fabric treatments, carpets/rugs, upholstered furniture, turnout gear, severe-wet outdoor apparel', 'Apparel excludes PPE and military-only clothing; exemptions for used goods, ≥85% recycled content, products made before the ban', 'Intentionally added', None, '', '', datetime.date(2028, 1, 1), 'Banned', '', 'High', 'CTG; CTDEEP'),
('CO-1', 'Colorado', 'SB24-081', 'Disclosure', 'Outdoor apparel for severe wet conditions', "Applies 2025-01-01 to 2027-12-31; wording 'Made with PFAS chemicals' per BCLP (confirm in statute)", 'Intentionally added', None, '', '', datetime.date(2025, 1, 1), 'Disclosure label incl. online listings', 'Label disclosure', 'Medium', 'COLEG; BCLPCO'),
('CO-2', 'Colorado', 'SB24-081', 'Sales ban', 'Textile articles incl. apparel, accessories, backpacks, handbags; severe-wet outdoor apparel', '', 'Intentionally added', None, '', '', datetime.date(2028, 1, 1), 'Banned', '', 'Medium', 'COLEG; BCLPCO; BHFS'),
('CO-3', 'Colorado', 'HB22-1345', 'Sales ban', 'Indoor textile furnishings and upholstered furniture (2025); outdoor textile furnishings (2027)', 'Outdoor furnishings from 2027-01-01', 'Intentionally added', None, '', '', datetime.date(2025, 1, 1), '', '', 'Medium', 'BHFS; ML26'),
('WA-1', 'Washington', 'WAC 173-337-110 (WSR 25-24-007)', 'Manufacture/sales ban', 'Apparel and accessories (leather, natural, synthetic or technical textiles)', 'Excludes apparel for extreme and extended use (reporting instead), specialty PPE, and products made before 2027-01-01; total fluorine >50 ppm creates a rebuttable presumption of intentional addition', 'Intentionally added; total fluorine presumed intentional above', 50, 'ppm total F', 'Total fluorine (EN ISO 20999 style)', datetime.date(2027, 1, 1), 'Extreme/extended-use apparel: reporting (WA-2)', '', 'Medium', 'WAORDER; BVWA; EXPWA'),
('WA-2', 'Washington', 'Chapter 173-337 WAC', 'Reporting', 'Apparel for extreme and extended use; footwear', 'Covers products made from 2026-01-01; first notice due 2027-01-31, then annually by Jan 31', 'Intentionally added (50 ppm total F presumption)', None, '', '', datetime.date(2026, 1, 1), 'Reporting', 'Annual notice to Ecology', 'Medium', 'WAORDER; EXPWA'),
('WA-3', 'Washington', 'Chapter 173-337 WAC', 'Sales ban', 'Indoor leather and textile furniture and furnishings', '', 'Intentionally added', None, '', '', datetime.date(2026, 1, 1), '', '', 'Medium', 'ML26; SBI'),
('MN-1', 'Minnesota', "Amara's Law (Minn. Stat. 116.943)", 'Sales ban', 'Fabric treatments, textile furnishings, upholstered furniture, carpets/rugs, juvenile products (not general apparel)', '', 'Intentionally added', None, '', '', datetime.date(2025, 1, 1), '', '', 'Medium', 'MPCA; ML26'),
('MN-2', 'Minnesota', "Amara's Law; PRISM reporting rule", 'Reporting', 'Products with intentionally added PFAS incl. apparel', 'Deadline moved to 2026-09-15 (2026-12-14 with approved extension); new products by Feb 1 each year; $800 initial fee', 'Intentionally added', None, '', '', datetime.date(2026, 9, 15), '', 'PRISM report + fee', 'Medium', 'FDMN'),
('MN-3', 'Minnesota', "Amara's Law", 'Sales ban (all products)', 'All products incl. apparel', 'Unless use designated currently unavoidable', 'Intentionally added', None, '', '', datetime.date(2032, 1, 1), 'Covered', '', 'High', 'TS; MPCA'),
('RI-1', 'Rhode Island', 'R.I. Gen. Laws §23-18.18-4(b)(2)', 'Ban with disclosure exception', 'Outdoor apparel for severe wet conditions', 'No 2026 duty; interaction with the 2027 textile ban not clearly resolved', 'Intentionally added', None, '', '', datetime.date(2029, 1, 1), "Sale only with 'Made with PFAS chemicals' disclosure", 'Label disclosure', 'High', 'RIDEM; RIBILL'),
('RI-2', 'Rhode Island', 'R.I. Gen. Laws §23-18.18-4(a)', 'Sales ban', 'Textile articles incl. apparel, accessories, footwear, handbags, backpacks, textile furnishings, bedding; fabric treatments; carpets/rugs', 'Processing agents count if PFAS detected in the final product; 2026 amendment H7734 adds DEM exemption authority', 'Intentionally added', None, '', '', datetime.date(2027, 1, 1), '', 'Certificate or seller notice within 30 days of a DEM request', 'High', 'RIDEM; RIBILL; SGSRI'),
('NM-1', 'New Mexico', 'PFAS Protection Act (HB 212), §5', 'Reporting', 'All non-exempt products with intentionally added PFAS', 'From 2028-01-01, unreported products may not be sold', 'Intentionally added', None, '', '', datetime.date(2027, 1, 1), '', 'Report to NMED', 'High', 'NMHB; NMED'),
('NM-2', 'New Mexico', '20.13.2 NMAC', 'Labeling (enjoined)', 'Products made from 2027-01-01', 'Preliminarily enjoined 2026-09-16 (ACC v. Kenney, D.N.M.); scope of injunction unclear — monitor', 'Intentionally added', None, '', '', datetime.date(2027, 1, 1), '', "Flask label marked 'PFAS' (enjoined)", 'Medium', 'FDNM; NMED'),
('NM-3', 'New Mexico', 'PFAS Protection Act (HB 212)', 'Sales ban', 'Textiles (any item made wholly or partly of fiber, yarn or fabric), textile furnishings, fabric treatments, carpets, upholstered furniture', 'No severe-wet outdoor apparel provision', 'Intentionally added', None, '', '', datetime.date(2028, 1, 1), 'Covered', '', 'High', 'NMHB; NMED'),
('NH-1', 'New Hampshire', 'RSA 149-M:64', 'Sales ban', 'Textile furnishings, textile treatments, upholstered furniture, carpets/rugs, juvenile products (apparel not named)', 'Exemptions: ≥85% recycled content, products made before the ban', 'Intentionally added', None, '', '', datetime.date(2027, 1, 1), '', '', 'High', 'NHRSA'),
('EU-1', 'EU', 'Regulation (EU) 2024/2462 (PFHxA)', 'Restriction', 'Clothing, accessories, footwear, consumer mixtures', 'Per homogeneous material; 1,000 ppb for PFHxA-related substances', 'PFHxA and salts (targeted)', 25, 'ppb', 'EN 17681-1 (LC-MS/MS)', datetime.date(2026, 10, 10), '', '', 'High', 'TS'),
('EU-2', 'EU', 'Regulation (EU) 2024/2462 (PFHxA)', 'Restriction', 'Home textiles: carpets, curtains, upholstery, bed linen, tablecloths', '', 'PFHxA and salts (targeted)', 25, 'ppb', 'EN 17681-1 (LC-MS/MS)', datetime.date(2027, 10, 10), '', '', 'High', 'TS'),
('EU-3', 'EU', 'POPs Regulation (PFOA)', 'Restriction', 'All articles', '1 mg/kg for PFOA-related compounds', 'PFOA and salts (targeted)', 25, 'ppb', 'EN 17681-1', datetime.date(2020, 7, 4), '', '', 'High', 'TS'),
('EU-4', 'EU', 'REACH Annex XVII entry 68 (C9-C14 PFCAs)', 'Restriction', 'All articles', '260 ppb for related substances', 'C9-C14 PFCAs (targeted)', 25, 'ppb', 'EN 17681-1', datetime.date(2023, 2, 25), '', '', 'High', 'TS'),
('EU-5', 'EU', 'Universal PFAS restriction (proposal)', 'Proposed restriction', 'Broad, with time-limited derogations', 'SEAC opinion expected end-2026; adoption years away', 'TBD', None, '', '', None, 'Interim derogations expected', '', 'Medium', 'WP'),
('FR-1', 'France', 'Law 2025-188', 'Manufacture/import/sales ban', 'Consumer clothing, footwear, waterproofing agents', 'Protective and defence clothing exempt; recycled-content tolerance', 'Targeted single PFAS 25 ppb; sum 250 ppb; total F incl. polymers', 50, 'ppm total F', 'EN 17681-1 + EN ISO 20999', datetime.date(2026, 1, 1), '', '', 'High', 'TS'),
('FR-2', 'France', 'Law 2025-188', 'Manufacture/import/sales ban', 'All textile products', 'Except essential uses, sovereignty uses, industrial technical textiles', 'As FR-1', 50, 'ppm total F', 'EN 17681-1 + EN ISO 20999', datetime.date(2030, 1, 1), '', '', 'High', 'TS'),
('DK-1', 'Denmark', 'BEK nr 464 of 2025', 'Import/sales ban', 'Private-use clothing, footwear, waterproofing agents', 'Applies per component article', 'Total fluorine', 50, 'mg F/kg', 'EN ISO 20999 (combustion IC)', datetime.date(2026, 7, 1), '', '', 'High', 'TS')]

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
["Rules verified against statutes and agency pages for CT, RI, VT, ME, CA (AB 347), NM and NY DEC on Oct 30, 2026; WA, MN and CO rely partly on 2025–2026 law-firm and lab alerts. Rules sheet: one row per obligation. Status and Days-until columns are formulas driven by the reference date (yellow cell B4; type =TODAY() to make it live)."],
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
CODES={'CA-1': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'CA-2': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'CA-3': ('severe_wet', 'intent_or_tof'), 'CA-6': ('severe_wet', 'obligation'), 'CA-4': ('apparel,accessories,home_textiles,severe_wet,footwear', 'obligation'), 'CA-5': ('apparel,accessories,home_textiles,severe_wet,footwear', 'obligation'), 'NY-1': ('apparel', 'ban_intent'), 'NY-2': ('apparel', 'tbd'), 'NY-3': ('severe_wet', 'ban_intent'), 'ME-1': ('apparel,accessories,home_textiles', 'ban_intent'), 'ME-2': ('severe_wet', 'obligation'), 'ME-3': ('all', 'ban_intent'), 'VT-1': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'VT-2': ('apparel,accessories,home_textiles', 'intent_or_tof'), 'VT-3': ('severe_wet', 'intent_or_tof'), 'CT-1': ('severe_wet', 'obligation'), 'CT-2': ('apparel,home_textiles,severe_wet', 'obligation'), 'CT-3': ('apparel,home_textiles,severe_wet', 'ban_intent'), 'CO-1': ('severe_wet', 'obligation'), 'CO-2': ('apparel,accessories,home_textiles,severe_wet', 'ban_intent'), 'CO-3': ('home_textiles', 'ban_intent'), 'WA-1': ('apparel,accessories', 'intent_or_total_f'), 'WA-2': ('severe_wet,footwear', 'obligation'), 'WA-3': ('home_textiles', 'ban_intent'), 'MN-1': ('home_textiles', 'ban_intent'), 'MN-2': ('all', 'obligation'), 'MN-3': ('all', 'ban_intent'), 'RI-1': ('severe_wet', 'obligation'), 'RI-2': ('apparel,accessories,footwear,home_textiles', 'ban_intent'), 'NM-1': ('all', 'obligation'), 'NM-2': ('all', 'obligation'), 'NM-3': ('apparel,accessories,footwear,home_textiles,severe_wet', 'ban_intent'), 'NH-1': ('home_textiles', 'ban_intent'), 'EU-1': ('apparel,accessories,footwear,severe_wet', 'targeted:PFHxA'), 'EU-2': ('home_textiles', 'targeted:PFHxA'), 'EU-3': ('all', 'targeted:PFOA'), 'EU-4': ('all', 'targeted:C9-C14 PFCAs'), 'EU-5': ('all', 'tbd'), 'FR-1': ('apparel,footwear,severe_wet', 'total_f'), 'FR-2': ('apparel,accessories,footwear,home_textiles,severe_wet', 'total_f'), 'DK-1': ('apparel,footwear,severe_wet', 'total_f')}
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
TITLES={'ML': 'Morgan Lewis (2024): New York and California bans on PFAS in textiles and apparel', 'VEN': 'Venable via Mondaq (2024): Fashion industry beware — PFAS bans on apparel', 'TS': 'Textile School: PFAS in textiles — limits, dates and test methods by market', 'FOX': 'Fox Rothschild (Sept 2026): State regulation of PFAS in the fashion industry', 'MD': 'Manufacturing Dive (2026): State PFAS laws taking effect in 2026', 'GK': 'Godfrey & Kahn: Patchwork of state PFAS regulations', 'WP': 'WavePLM (2026): PFAS in clothing — what brands must test, disclose and fix', 'ML26': 'Morgan Lewis (Jan 2026): State regulation of PFAS in consumer products in 2026', 'SBI': 'SBI Finishing: PFAS-free stain protection and 2026 state bans', 'CTG': 'Connecticut General Assembly: Conn. Gen. Stat. ch. 446z (§22a-903c)', 'CTDEEP': 'CT DEEP: PFAS in products', 'RIDEM': 'Rhode Island DEM: PFAS in products', 'RIBILL': 'Rhode Island H7356 Sub A (2024) bill text', 'SGSRI': 'SGS (June 2026): Rhode Island revises PFAS ban (H7734)', 'VTAG': 'Vermont Attorney General: guidance on PFAS product bans (Nov 2025)', 'VTACT': 'Vermont Act 54 (2025) as enacted', 'MESTAT': 'Maine statute 38 M.R.S. §1614', 'MEDEP': 'Maine DEP: PFAS in products', 'DD347': 'CalMatters Digital Democracy: AB 347 chaptered text', 'BCLP347': 'BCLP: California enacts PFAS enforcement and registration law', 'KDCA': "Kelley Drye: Preparing for California's ban on PFAS in textiles", 'COLEG': 'Colorado General Assembly: SB24-081', 'BCLPCO': 'BCLP: Colorado increases restrictions on PFAS in consumer products', 'BHFS': 'Brownstein: Colorado expands PFAS labeling and phase-out rules', 'WAORDER': 'Washington Ecology: adoption order WSR 25-24-007', 'BVWA': 'Bureau Veritas: Washington finalizes Cycle 1.5 PFAS rule', 'EXPWA': 'Exponent: Washington adopts new PFAS restrictions and reporting', 'FDMN': 'Faegre Drinker (Apr 2026): Minnesota PFAS reporting deadline extension', 'MPCA': 'Minnesota PCA: PFAS prohibitions presentation (2024)', 'NMHB': 'New Mexico HB 212 (2025) final text', 'NMED': 'New Mexico Environment Dept: PFAS Protection Act', 'FDNM': 'Faegre Drinker (Sept 2026): court blocks New Mexico PFAS labeling', 'NYDEC': 'NY DEC: PFAS in apparel law', 'NHRSA': 'New Hampshire RSA 149-M:64'}
so.append(["Key","URL","Title"])
for k,u in S.items(): so.append([k,u,TITLES.get(k,"")])
for row in so.iter_rows():
    for cell in row: cell.font=base
for c in (1,2,3): so.cell(1,c).font=hdr_font; so.cell(1,c).fill=hdr_fill
so.column_dimensions["C"].width=80
so.column_dimensions["A"].width=8; so.column_dimensions["B"].width=110

import sys; wb.save(sys.argv[1] if len(sys.argv) > 1 else "rules.xlsx")
print(len(R),"rules")
