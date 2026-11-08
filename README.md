# 公開買付けの取引条件と公表後の株価変動 — 再現用のプログラム

この README は、社会科学のデータ編集者による共通の様式（Social Science Data Editors, *Template README for Social Science Replication Packages*）の章立てに従っている。

## 概要

卒業論文「公開買付けの取引条件と公表後の株価変動」（慶應義塾大学経済学部、2026年度）の分析に用いたプログラムである。`code/run_all.py` を実行すると、公開書類と株価から変数を作り（`code/01_dataprep/`）、論文のすべての表・図と本文中の数値を作る（`code/02_analysis/`）。手作業による途中の操作はない。手元の計算機（下記）で全体の実行に約4分かかる。

## データの入手可能性と出所

データはこのリポジトリに含めていない。株価は第三者のサイトから取得したものであり、再配布できないためである。

| データ | 出所 | 置き場所 |
|---|---|---|
| 公開買付届出書・意見表明報告書（PDF） | EDINET（金融庁の電子開示システム） | `RAW_DATA/data/edinet_pdf/` |
| 公開買付けの適時開示（2019・2021年） | TDnet（東京証券取引所の適時開示情報伝達システム）。IR BANK に保存されたものを取得 | `RAW_DATA/data_old/pdf/`、`RAW_DATA/data_old/text/` |
| 日次株価・TOPIX ETF | IR BANK | `RAW_DATA/data*/prices/`、`RAW_DATA/data*/index_topix_etf*.csv` |
| 報道の見出し | 株探（kabutan.jp）、Google ニュースで検索した日本経済新聞の見出し | `RAW_DATA/data*/news*/`、`RAW_DATA/attention/` |
| 案件の一覧 | TDnet の公開買付けの開示から作成した表 | `data/inputs/` |

`RAW_DATA` は環境変数 `THESIS_RAW_DATA` で指定する（指定しなければ、このリポジトリの1つ上のフォルダ）。

## 計算環境

- Python 3.12.3。パッケージとその版は `requirements.txt` に記す（pandas 3.0.5、numpy 2.5.2、scipy 1.18.0、statsmodels 0.15.0、scikit-learn 1.9.0、matplotlib 3.11.1、pymupdf 1.28.0）。
- 図の日本語にはヒラギノ明朝 ProN（macOS 標準）を使う。
- 乱数：予測のブートストラップ区間は `numpy.random.default_rng(0)` で固定している。
- 実行した計算機：Apple M2、メモリ 8GB、macOS 15.7。全体の実行時間は約4分。

## プログラムの説明

- `code/config.py`：データの置き場所と、分析で固定する値（書類の提出期限の15時、張り付きの閾値1%、部分買付けを分ける価格差2%、標本の件数など）をすべてここで一度だけ定める。
- `code/01_dataprep/`：公開書類と株価から変数を作り、案件ごとの分析表 `data/processed/analysis_table.csv` にまとめる。分析表の各列の意味は `data/codebook.csv` に記す。
  - `01_compute_price_gap.py`：J（公表後最初の取引日）、買付プレミアム、計算開始日の価格差 S_i
  - `02_compute_return_to_initial_end.py`：当初の買付期間の末日と収益率 R_i
  - `03_compute_sentiment_scores.py`：報道見出しと意見表明報告書の語調（辞書法）
  - `04_extract_deal_terms.py`：11項目の取引条件をキーワードと数値の規則で判定する（規則は `deal_term_rules.py`。生成AIは使わない）
  - `05_compute_attention_measures.py`：市場の注目度の指標
  - `06_build_analysis_table.py`：分析表を作る
  - `07_check_offer_prices.py`：分析に使った買付価格が原文の買付価格と一致するかを1件ずつ確かめる
- `code/02_analysis/`：論文の表・図を1つずつ作る。ファイル名は「表・図の番号＋内容」である。`sample.py` が分析対象の403件を読み込み、件数が論文と違えば止まる。

## 再現の手順

1. `pip install -r requirements.txt`
2. 上の表のデータを `RAW_DATA` に置き、`data/inputs/` に案件の一覧を置く。
3. `python code/run_all.py`

結果は `output/tables/`（表）と `output/figures/`（図）に出力される。

## 表・図とプログラムの対応表

| 表・図 | プログラム | 出力ファイル | 備考 |
|---|---|---|---|
| 表3.1 分析対象の選定 | `code/02_analysis/table3_1_sample_selection.py` | `table3_1_sample_selection.csv` | |
| 表3.2 年別の件数 | `code/02_analysis/table3_2_and_3_3_deals_by_year_and_descriptive_statistics.py` | `table3_2_deals_by_year.csv` | |
| 表3.3 収益率と価格差の記述統計 | 同上 | `table3_3_descriptive_statistics.csv` | |
| 図3.1 収益率と価格差の分布 | `code/02_analysis/figure3_1_return_and_price_gap_distribution.py` | `figure3_1_return_and_price_gap_distribution.png` | |
| 3.5節 独立の読み取りとの一致 | `code/02_analysis/validation_independent_reading.py` | `validation_independent_reading.csv` | |
| 3.5節 生成AIの判定との一致 | `code/01_dataprep/04_extract_deal_terms.py` | `deal_terms_agreement_with_ai.csv` | |
| 3.3節 買付価格の照合 | `code/01_dataprep/07_check_offer_prices.py` | `offer_price_check.csv` | |
| 図4.1 案件の分け方の手順 | `code/02_analysis/figure4_1_classification_of_deals.py` | `figure4_1_classification_of_deals.png` | 件数はデータから計算する |
| 図4.2 価格差の絶対値の分布 | `code/02_analysis/figure4_2_absolute_price_gap_distribution.py` | `figure4_2_absolute_price_gap_distribution.png` | |
| 表4.1 案件の種類ごとの記述統計 | `code/02_analysis/table4_1_descriptive_statistics_by_group.py` | `table4_1_descriptive_statistics_by_group.csv` | |
| 図4.3 価格差と収益率の関係 | `code/02_analysis/figure4_3_price_gap_and_return.py` | `figure4_3_price_gap_and_return.png` | |
| 第3・4章の本文中の数値 | `code/02_analysis/numbers_in_text.py` | `numbers_in_text.txt` | |
| 第5章 回帰分析 | `code/02_analysis/table5_regressions.py R1` | `table5_regressions_R1.csv` | 表番号は第5章の執筆後に記す |
| 第5章 予測誤差の比較 | `code/02_analysis/table5_prediction_errors.py R1` | `table5_prediction_errors_R1.csv` | |
| 第5章 市場の注目度 | `code/02_analysis/table5_attention.py` | `table5_attention.csv` | |
| 頑健性：TOPIX を引いた収益 | `table5_regressions.py W1`、`table5_prediction_errors.py W1` | `table5_regressions_W1.csv`、`table5_prediction_errors_W1.csv` | |
| 頑健性：書類の規則の境界にある4件を加える | `table5_regressions.py R1 --include-boundary-deals` | `table5_regressions_R1_including_boundary_deals.csv` | |
| 頑健性：閾値を変える | `code/02_analysis/robustness_thresholds.py` | `robustness_thresholds.csv` | |

## 参考文献

- Gentzkow, M. and J. M. Shapiro (2014) *Code and Data for the Social Sciences: A Practitioner's Guide*.
- Social Science Data Editors, *Template README for Social Science Replication Packages*, https://social-science-data-editors.github.io/template_README/
- Hsieh, J. and R. A. Walkling (2005) "Determinants and Implications of Arbitrage Holdings in Acquisitions," *Journal of Financial Economics* 77(3), 605–648.
