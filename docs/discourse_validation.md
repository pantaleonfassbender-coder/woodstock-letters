# The edition's measures against the study's replication package

Written by `tools/validate_discourse.py`. The study: P. Fassbender, “Identity and Values in U.S. Jesuit Discourse, 1890–1944”, replication package, CC BY 4.0, https://doi.org/10.5281/zenodo.22697014. Each of the package's per-article files of the Woodstock Letters is matched to the edition's article by its words, and scored from the edition's text with the package's word lists, filters, sentence count and MATTR (`tools/build_discourse.py`).

## Agreement, per text (n = 22)

| Measure | r | mean abs. difference | package mean |
|---|---|---|---|
| i | 0.994 | 0.041 | 0.575 |
| we | 1.000 | 0.005 | 0.788 |
| certainty | 1.000 | 0.002 | 0.320 |
| achievement | 1.000 | 0.002 | 0.239 |
| affiliation | 1.000 | 0.007 | 1.197 |
| power | 1.000 | 0.005 | 0.792 |
| posemo | 1.000 | 0.004 | 0.547 |
| negemo | 1.000 | 0.001 | 0.174 |
| future | 1.000 | 0.002 | 0.266 |
| WPS | 0.992 | 0.45 | 23.25 |
| words | 1.000 | ratio 0.997 | 3329 |

## The study's corpus means (Table 2), recomputed

Word-count-weighted means over the non-optional texts of each year, from the package's values and from the edition's.

| Year | words | WPS | I % | we % | certainty % | achievement % |
|---|---|---|---|---|---|---|
| 1900 (package) | 17,978 | 24.6 | 0.54 | 0.77 | 0.45 | 0.22 |
| 1900 (edition) | 18,004 | 24.7 | 0.48 | 0.78 | 0.45 | 0.22 |
| 1910 (package) | 25,644 | 20.5 | 0.25 | 0.61 | 0.26 | 0.18 |
| 1910 (edition) | 25,423 | 20.6 | 0.20 | 0.61 | 0.26 | 0.18 |
| 1930 (package) | 17,253 | 21.7 | 0.23 | 0.46 | 0.24 | 0.20 |
| 1930 (edition) | 17,265 | 21.9 | 0.23 | 0.46 | 0.24 | 0.20 |

The small difference in first-person singular is the package's: its OCR texts keep "I^oyola", "I^etters", "I^ouis" (the L read as I^), which its tokeniser counts as the pronoun *I*; the edition repairs them to Loyola, Letters, Louis.


## The corpora of 1890 and 1920

The package gives the 1890 sample and the Golden Jubilee essays of 1920 as one cleaned file each. Their words are those of whole articles of the edition, found by shared runs of eight words.

| Year | Articles | words (pkg / ed.) | we % | I % | certainty % | achievement % |
|---|---|---|---|---|---|---|
| 1890 | [19-003](../#/a/19-003) Archbishop Satolli at Woodstock; [19-179](../#/a/19-179) Spain; [19-396](../#/a/19-396) Retractation of Clement XIV | 4,864 / 4,755 | 1.19 / 1.22 | 0.45 / 0.50 | 0.23 / 0.23 | 0.31 / 0.32 |
| 1920 | [49-001](../#/a/49-001) The Golden Jubilee; [49-006](../#/a/49-006) The Academy in Honor of the Cardinal | 7,773 / 7,806 | 2.03 / 2.04 | 0.53 / 0.54 | 0.33 / 0.33 | 0.37 / 0.37 |

Package / edition. The study's commemorative register is thus the Woodstock jubilee itself. Other anniversary pieces (the Spring Hill centennial, the Papal Jubilee celebration, the Auriesville celebration of 1930) stand in its ordinary series, and their first-person plural is low (0.12–0.48 %). The edition's automatic commemorative flag is wider (every piece whose title names a jubilee, centenary or anniversary, and the whole of an issue given to a jubilee), so its annual contrast is weaker than the study's.


## Per text

| Package file | Edition article | Register | words (pkg / ed.) | we % (pkg / ed.) |
|---|---|---|---|---|
| 1900_arms_of_loyola.txt | [29-120](../#/a/29-120) The Arms of Loyola and the Battle of Beotibar | essay | 949 / 954 | 1.26 / 1.26 |
| 1900_badge_of_loyola.txt | [29-001](../#/a/29-001) The Badge of Loyola | essay | 2244 / 2241 | 1.11 / 1.12 |
| 1900_bc_harvard.txt | [29-337](../#/a/29-337) Boston College and Harvard University | essay | 1182 / 1180 | 0.34 / 0.34 |
| 1900_catholic_colleges_conf.txt | [29-342](../#/a/29-342) Ours at the Second Annual Conference of Catholic Colleges | essay | 896 / 896 | 0.45 / 0.45 |
| 1900_nea_chicago_OPT.txt | [29-123](../#/a/29-123) Meeting of the N. E. A. at Chicago | essay | 5594 / 5586 | 0.61 / 0.61 |
| 1900_oxford_st_marys.txt | [29-283](../#/a/29-283) The Oxford and St. Mary's Course for Ours | essay | 5341 / 5337 | 0.81 / 0.81 |
| 1900_woodstocks_founders.txt | [29-296](../#/a/29-296) Two of Woodstock's Founders | essay | 7366 / 7396 | 0.69 / 0.70 |
| 1910_brooklyn_college.txt | [39-167](../#/a/39-167) Brooklyn College | essay | 5427 / 5425 | 1.09 / 1.09 |
| 1910_curia_father_general.txt | [39-001](../#/a/39-001) The Curia of Father General | essay | 10223 / 10220 | 0.29 / 0.29 |
| 1910_jesuit_farms_maryland.txt | [39-374](../#/a/39-374) The Jesuit Farms in Maryland | essay | 3778 / 3513 | 0.66 / 0.68 |
| 1910_new_province_california.txt | [39-079](../#/a/39-079) The New Province of California | essay | 454 / 464 | 0.44 / 0.43 |
| 1910_odd_road_to_rome_OPT.txt | [39-208](../#/a/39-208) An Odd Road to Rome | essay | 1343 / 1344 | 2.53 / 2.53 |
| 1910_st_stanislaus.txt | [39-347](../#/a/39-347) St. Stanislaus Seminary | letter | 5762 / 5801 | 0.69 / 0.69 |
| 1910_working_men_exercises_OPT.txt | [39-091](../#/a/39-091) The Spiritual Exercises for Men and for Working-men | letter | 2028 / 1979 | 1.92 / 1.97 |
| 1930_auriesville.txt | [59-309](../#/a/59-309) Auriesville Celebration in Honor of the Canonization of the North American Martyrs | essay | 3432 / 3437 | 0.12 / 0.12 |
| 1930_church_and_radio.txt | [59-053](../#/a/59-053) The Church and the Radio | essay | 1382 / 1383 | 0.94 / 0.94 |
| 1930_jesuit_seminary_news.txt | [59-021](../#/a/59-021) The Inception of the Jesuit Seminary News | essay | 648 / 650 | 0.46 / 0.46 |
| 1930_papal_jubilee_woodstock.txt | [59-239](../#/a/59-239) Papal Jubilee Celebration | essay | 2311 / 2309 | 0.48 / 0.48 |
| 1930_pre_emancipation_OPT.txt | [59-023](../#/a/59-023) A Pre-emancipation Jesuit | essay | 3399 / 3396 | 0.53 / 0.53 |
| 1930_spring_hill.txt | [59-335](../#/a/59-335) Spring Hill Observes Centennial | essay | 4177 / 4180 | 0.41 / 0.41 |
| 1930_walsh_time.txt | [59-222](../#/a/59-222) A Record of the Controversy Between Fr. Edmund A. Walsh and Time | essay | 3554 / 3555 | 0.31 / 0.31 |
| 1930_weston_college.txt | [59-217](../#/a/59-217) Weston College | essay | 1749 / 1751 | 1.20 / 1.20 |
