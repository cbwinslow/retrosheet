# Retrosheet Documentation Index

This file catalogs the main public documentation on Retrosheet’s site that describes data formats, IDs, tools, and usage guidelines, with stable URLs and brief notes for each item. [page:1][page:2][web:2][web:6][web:7][web:8][web:9][web:10][web:11][web:13][web:14]

---

## 1. Core “How to Use” Documentation

### 1.1 Retrosheet Documentation Hub

- Title: Retrosheet Documentation
- URL: https://www.retrosheet.org/docs.htm
- Notes: Landing page that links to the original “How to Use Our Event File (Game) Data” document plus several key reference files such as hit location and ballpark codes. [page:1]

### 1.2 How to Use Our Event Files (HTML)

- Title: How to Use Our Event Files
- URL: https://www.retrosheet.org/datause.html
- Notes: HTML version of instructions for working with event (play‑by‑play) files, including references to BEVENT and BGAME utilities, command‑line usage, and pre‑parsed play‑by‑play data. [web:6]

### 1.3 How to Use Our Event File (Game) Data – Downloadable Formats

These are the same content as the HTML instructions, in alternate formats. [page:1]

- Microsoft Word: https://www.retrosheet.org/datause.doc
- Rich Text Format: https://www.retrosheet.org/datause.rtf
- Plain Text: https://www.retrosheet.org/datause.txt

### 1.4 Step‑by‑Step Example

- Title: Step‑by‑Step Example
- URL: https://www.retrosheet.org/stepex.txt
- Notes: Text walkthrough demonstrating the process of using Retrosheet event data and tools. [page:1]

---

## 2. Event / Game File Specifications

### 2.1 Event File Overview Page

- Title: Play‑by‑Play Data Files (Event Files)
- URL: https://www.retrosheet.org/game.htm
- Notes: Main hub for event files, linking to the detailed file format specification, usage notes, rosters, IDs, and download archives for regular season, postseason, All‑Star, Negro Leagues, and discrepancy files. [page:2]

### 2.2 Detailed Description of Event File Contents

- Title: Retrosheet Event Files – Detailed Description
- URL: https://www.retrosheet.org/eventfile.htm
- Notes: Canonical specification for the event file format and scoring system, covering record types (id, version, info, start, play, sub, com, data), record ordering, and the full list of info fields. [web:2][web:14]

### 2.3 Overview of Game Account Files (PDF)

- Title: Overview of Game Account Files
- URL: https://www.retrosheet.org/GameFiles.pdf
- Notes: PDF overview that explains structure and organization of game account files, complementing the detailed event file spec. [page:2]

### 2.4 Box Score Event File Specification

- Title: Box Score Event Files
- URL: https://www.retrosheet.org/boxfile.txt
- Notes: Text specification describing additional record types used in “Box Score Event Files” (.eba, .ebn) for games without complete play‑by‑play, including versioning and new records’ semantics. [web:9][page:2]

### 2.5 Notices About Use and Limitations of Data

- Title: Notices (Use and Limitations of Data)
- URL: https://www.retrosheet.org/notice.txt
- Linked from: https://www.retrosheet.org/game.htm#Notice
- Notes: Legal / policy text on permitted uses of Retrosheet data, attribution requirements, and accuracy disclaimers. [page:2]

---

## 3. Supporting Reference Files

### 3.1 Hit Location Diagram

- Title: Hit Location Diagram
- URL: https://www.retrosheet.org/location.htm
- Notes: Diagram and explanation of hit location codes used in event files (e.g., “7/F78D”), with a field map and examples. [page:1][web:13]

### 3.2 Ballpark Codes

There are two main ballpark code resources. [page:1][page:2]

- Ballpark Codes for `info,site`:
  - URL (text): https://www.retrosheet.org/parkcode.txt
  - Notes: List of ballpark codes used in the `info,site` field in event files.
- Ballpark Codes (zip archive):
  - URL: https://www.retrosheet.org/ballparks.zip
  - Notes: Downloadable data with ballpark information (codes plus additional metadata). [page:2]

### 3.3 Franchise / Team IDs

- Title: Franchise/Team IDs
- URL: https://www.retrosheet.org/teams.zip
- Notes: Compressed data listing franchises and team identifiers referenced throughout Retrosheet data. [page:2]

### 3.4 Player / Staff IDs

- Title: Player, Manager, Coach, Umpire IDs
- URL: https://www.retrosheet.org/biofile.zip
- Notes: Zip archive of bio/ID files defining the identifiers used for players, managers, coaches, and umpires in event and roster data. [page:2]

### 3.5 Annual Rosters

- Title: Annual Rosters, 1871–2025
- URL: https://www.retrosheet.org/rosters.zip
- Notes: Combined download of season‑by‑season roster files for all teams from 1871 through 2025. [page:2]

---

## 4. Parsed and Derived Data Documentation

### 4.1 Parsed Play‑by‑Play Data

- Title: Parsed Play‑by‑Play Data
- URL: https://retrosheet.org/downloads/plays.html
- Notes: Describes the pre‑parsed play‑by‑play datasets Retrosheet provides, including columns and a crosswalk to the BEVENT output format. [web:8]

### 4.2 Working with Event Files (BEVENT/BGAME)

- Title: Working with Event Files
- URL: https://www.retrosheet.org/datause.html
- Notes: Documents Retrosheet’s BEVENT and BGAME utilities, usage with the `-y` year switch, required companion files, and sample shell commands. [web:6]

### 4.3 Discrepancy Files

- Title: Discrepancy Files by Decade
- URL: Linked from: https://www.retrosheet.org/game.htm (e.g., https://www.retrosheet.org/1910sdis.zip etc.)
- Notes: Describes/downloads discrepancy files noting differences between play‑by‑play data and official totals, grouped by decade. [page:2]

### 4.4 Negro League Event and Box‑Score Files

- Title: Negro League Event Files / Box‑Score Files
- URLs:
  - Event files: https://www.retrosheet.org/events/allevr.zip
  - Box‑score files: https://www.retrosheet.org/events/allebr.zip
- Notes: Coverage for Negro League regular‑season, exhibition, All‑Star, and postseason games, with note that many accounts are deduced from newspaper sources. [page:2]

---

## 5. Site‑Wide Overviews and Resources

### 5.1 Retrosheet Web Site Overview

- Title: Retrosheet Web Site Overview
- URL: https://www.retrosheet.org/site.htm
- Notes: Narrative overview of the site’s contents (Negro Leagues, data downloads, features, organization, archives) and positioning as an extensive baseball data resource. [web:10]

### 5.2 Retrosheet Site Map

- Title: Retrosheet Site Map
- URL: https://www.retrosheet.org/sitemap.htm
- Notes: HTML site map enumerating main sections (games, features, rules history, schedules, data downloads, etc.), plus update timestamp and copyright notice. [web:7]

### 5.3 Frequently Asked Questions

- Title: Frequently Asked Questions – Retrosheet
- URL: https://www.retrosheet.org/faq.htm
- Notes: Policy‑oriented documentation (e.g., posting policy, proofing and comparison to official totals) and general explanatory material about Retrosheet’s data and processes. [web:4]

### 5.4 Data Resources Page

- Title: Data Resources
- URL: https://www.retrosheet.org/resources/resources1.html
- Notes: Curated list of external data resources and projects built on Retrosheet data, including a GitHub project that organizes data for relational databases. [web:11]

---

## 6. Download Indexes (Context for Data Use)

These are not “documentation” in prose but are important index pages for obtaining the data described above. [page:2]

- Event file index (regular/postseason/All‑Star/Negro Leagues):
  - URL: https://www.retrosheet.org/game.htm
- Regular‑season event files by year and decade:
  - Example: https://www.retrosheet.org/events/2025eve.zip
  - Decade bundles: https://www.retrosheet.org/events/2020seve.zip
- Regular‑season box score event files by year and decade:
  - Example: https://www.retrosheet.org/events/2025box.zip
  - Decade bundles: https://www.retrosheet.org/events/2020sbox.zip
- All‑Star and postseason complete sets:
  - All‑Star: https://www.retrosheet.org/events/allas.zip
  - Postseason: https://www.retrosheet.org/events/allpost.zip
  - All‑Star + postseason box‑score: https://www.retrosheet.org/events/allebe.zip

---

## 7. Notes for Integrating in Your Project

- The **primary technical specs** you will most often reference when parsing or generating Retrosheet‑compatible data are:
  - Event file detailed description: https://www.retrosheet.org/eventfile.htm
  - Box score event file spec: https://www.retrosheet.org/boxfile.txt
  - Hit location diagram: https://www.retrosheet.org/location.htm
  - ID/roster and team reference archives: biofile, rosters, ballparks, teams. [web:2][web:9][web:13][page:2]
- For **tooling and workflows**, the main reference is:
  - Working with Event Files (BEVENT/BGAME): https://www.retrosheet.org/datause.html
  - Parsed play‑by‑play data: https://retrosheet.org/downloads/plays.html. [web:6][web:8]


# Retrosheet – Special Features

> Source: https://www.retrosheet.org/specfeat.htm
> Last updated: April 6, 2026

These are items that do not fit neatly elsewhere on the Retrosheet site.
Links to them may also appear on other pages where you might not expect to find them.

---

## 1. Rules History

- **URL:** https://www.retrosheet.org/rules/rules.htm
- **Description:** An overview of changes in the playing rules and scoring rules of baseball over the past 150+ years. Compiled by Stew Thornley.

---

## 2. Regional/City Series

- **URL:** https://www.retrosheet.org/Regional%20Series
- **Description:** An extensive section about postseason series sanctioned by organized baseball, played from 1905–42, mostly in Chicago. Contains boxscores for all 190 games across the 32 series, with the vast majority having play-by-play accounts (some deduced). Based on over 20 years of research by Mike Cantor. Also includes descriptions of other series dating back to 1882 in an article by the late Fred Ivor-Campbell.

---

## 3. Sabermetric Bibliography

- **URL:** https://retrosheet.org/resources/pavitt.htm
- **Description:** A bibliography compiled by Charlie Pavitt with over 4,000 entries of sabermetric research papers, articles, and books. Last updated: November 2023.

---

## 4. Honoring Jackie Robinson

- **URL:** https://www.retrosheet.org/jackie.htm
- **Description:** Published in the year of the 60th anniversary of Jackie Robinson's major league debut. Contains an extensive amount of data about his playing performance.

---

## 5. History of Nicknames of Current Teams

- **URL:** https://www.retrosheet.org/Nickname.htm
- **Description:** A data file tracking the history of current MLB franchises — where they play, their leagues and divisions, and their most common nicknames over time.

---

## 6. In-Season Exhibition Games (ISEG)

Compiled originally by Walter LeConte; later revised by several contributors for the 1871–1920 period. Documents exhibition games played by major league teams during the regular season.

| # | Title | URL | Date |
|---|-------|-----|------|
| 1 | In Season Exhibition Games | https://www.retrosheet.org/ISEG.pdf | 2/11/2008 |
| 2 | ISEG Preface | https://www.retrosheet.org/ISEGpreface.pdf | 3/4/2013 |
| 3 | ISEG Update 2013 | https://www.retrosheet.org/ISEGUpdate.pdf | 3/4/2013 |
| 4 | Detailed List of ISEG 1871–1920 | https://www.retrosheet.org/InSeasonExhibitionGames1871-1920.htm | 6/26/2021 |
| 5 | Detailed List of ISEG 1921–2012 | https://www.retrosheet.org/InSeasonExhibitionGames1921-2012.htm | 3/4/2013 |

---

## 7. First Major League Game Ever Played

- **URL:** https://www.retrosheet.org/1stGame.htm
- **Description:** Full game details of the very first Major League game ever played.

---

## 8. 1871 Rules (Word Document)

- **URL:** https://www.retrosheet.org/1871Rules.doc
- **Description:** The official rules of baseball from 1871. Acts as a companion document to the first Major League game entry above.

---

## 9. Protoball Project

- **URL:** https://www.protoball.org/
- **Description:** An ongoing historical examination of "pre-baseball" games dating back hundreds of years. An external project linked from Retrosheet.

---

## 10. Retrosheet Scoring System History

- **URL:** https://www.retrosheet.org/sc-hist.htm
- **Description:** A brief history of the Retrosheet scoring system, including an example scoresheet.

---

## 11. Coors Field Construction Photo

- **URL:** https://www.retrosheet.org/coors05.jpg
- **Description:** A photograph of Coors Field being built. Used historically as the site's "under construction" page image.

---

## 12. Strange and Unusual Plays

- **URL:** https://www.retrosheet.org/strange.htm
- **Last Updated:** January 2002 *(infrequently updated since the newsletter was discontinued)*
- **Description:** A compilation of unbelievable, odd, and unusual plays discovered while processing scoresheets — including a strikeout where the batter was called out on play code 7-6-7. Compiled from the Retrosheet newsletter starting with Vol. 3, No. 3 (earlier issues called the section "Odd and Cute").

---

## Notes

- All data on Retrosheet is copyright © 1996–2026 by Retrosheet. All Rights Reserved.
- For usage terms, see: https://www.retrosheet.org/notice.txt
- Questions/comments: tthress [at] retrosheet.org
- Community discussion group: https://groups.io/g/RetroList
- Retrosheet is an all-volunteer 501(c)(3) charitable organization.
  Donations: https://www.retrosheet.org/donations.htm