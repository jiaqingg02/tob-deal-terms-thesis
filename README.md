# 公開買付けの取引条件と公表後の株価変動 — 再現用のプログラム

この README は、社会科学のデータ編集者による共通の様式（Social Science Data Editors, *Template README for Social Science Replication Packages*）の章立てに従っている。

## 概要

卒業論文「公開買付けの取引条件と公表後の株価変動」（慶應義塾大学経済学部、2026年度）の分析に用いたプログラムである。`code/run_all.py` を実行すると、公開書類と株価から変数を作り（`code/01_dataprep/`）、論文のすべての表・図と本文中の数値を作る（`code/02_analysis/`）。手作業による途中の操作はない。手元の計算機（下記）で全体の実行に約4分かかる。

## データの入手可能性と出所

株価と公開書類の原本はこのリポジトリに含めていない。株価は第三者のサイトから取得したものであり、再配布できないためである。公開書類はEDINETから誰でも取得できる。本稿で作成したデータのうち、株価を用いないものは `data/published/` に置いている（下記）。

| データ | 出所 | 置き場所 |
|---|---|---|
| 公開買付届出書・意見表明報告書（PDF） | EDINET（金融庁の電子開示システム） | `RAW_DATA/data/edinet_pdf/` |
| 公開買付けの適時開示（2019・2021年） | TDnet（東京証券取引所の適時開示情報伝達システム）。IR BANK に保存されたものを取得 | `RAW_DATA/data_old/pdf/`、`RAW_DATA/data_old/text/` |
| 日次株価・TOPIX ETF | IR BANK | `RAW_DATA/data*/prices/`、`RAW_DATA/data*/index_topix_etf*.csv` |
| 報道の見出し | 株探（kabutan.jp）、Google ニュースで検索した日本経済新聞の見出し | `RAW_DATA/data*/news*/`、`RAW_DATA/attention/` |
| 案件の一覧 | TDnet の公開買付けの開示から作成した表 | `data/inputs/` |

`data/published/` に置くデータ（`code/01_dataprep/08_export_published_data.py` が作成する）：

| ファイル | 内容 |
|---|---|
| `deal_list.csv` | 書類を読んだ413件の一覧。証券コード、公表日、計算開始日、二つの書類のEDINETの文書番号と提出日時、分析対象の403件に含まれるか |
| `deal_terms.csv` | 11の取引条件の判定（1・0。買付資金の記載がない案件は欠測） |
| `deal_term_evidence.csv` | 案件と条件ごとに、該当した規則、根拠の文、文書番号、頁 |
| `earlier_ai_judgments.csv` | 規則を作成する前に生成AIが行った判定（付録Aの照合にだけ用いる） |
| `deals_with_document_passages.csv` | 書類から段落を抜き出す453件と、書類の種類（EDINET の届出書・意見表明報告書、または TDnet の適時開示） |
| `document_check_of_disagreements_with_ai.csv` | 規則と生成AIの判定が一致しなかった箇所について、原文で確かめた値、理由、根拠の文、文書番号、頁 |

`RAW_DATA` は環境変数 `THESIS_RAW_DATA` で指定する（指定しなければ、このリポジトリの1つ上のフォルダ）。

## 計算環境

- Python 3.12.3。パッケージとその版は `requirements.txt` に記す（pandas 3.0.5、numpy 2.5.2、scipy 1.18.0、statsmodels 0.15.0、scikit-learn 1.9.0、matplotlib 3.11.1、pymupdf 1.28.0）。
- 届出書のテキスト化には Poppler の `pdftotext`（26.07.0）を使う。
- 図の日本語にはヒラギノ明朝 ProN（macOS 標準）を使う。
- 乱数：予測のブートストラップ区間は `numpy.random.default_rng(0)`、ランダムフォレストと勾配ブースティングは `random_state=0` で固定している。
- 実行した計算機：Apple M2、メモリ 8GB、macOS 15.7。全体の実行時間は約40分（大半は付録Dの全方法の比較）。

## プログラムの説明

- `code/config.py`：データの置き場所と、分析で固定する値（書類の提出期限の15時、付録で使う張り付きの閾値1%、標本の件数など）をすべてここで一度だけ定める。
- `code/01_dataprep/`：公開書類と株価から変数を作り、案件ごとの分析表 `data/processed/analysis_table.csv` にまとめる。分析表の各列の意味は `data/codebook.csv` に記す。
  - `00_cut_document_passages.py`：書類をテキストにし（届出書は `pdftotext -layout`、意見表明報告書と適時開示は PyMuPDF）、取引条件ごとに関係する箇所を見出しと語句で抜き出して、社名と証券コードを「■■」に置き換える。抜き出し方は `document_passage_cutting.py` に記す（付録Aの表A.1）
  - `01_compute_price_gap.py`：J（公表後最初の取引日）、買付プレミアム、計算開始日の価格差 S_i
  - `02_compute_return_to_initial_end.py`：当初の買付期間の末日と収益率 R_i
  - `03_compute_sentiment_scores.py`：報道見出しと意見表明報告書の語調（辞書法）
  - `04_extract_deal_terms.py`：11項目の取引条件をキーワードと数値の規則で判定する（規則は `deal_term_rules.py`。生成AIは使わない）。原文と照らして規則の判定が誤っていた箇所は、根拠の文・文書・ページとともに `corrections_after_document_check.csv` に記し、この表に従って修正する
  - `05_compute_attention_measures.py`：市場の注目度の指標
  - `06_build_analysis_table.py`：分析表を作る
  - `07_check_offer_prices.py`：分析に使った買付価格が原文の買付価格と一致するかを1件ずつ確かめる
  - `08_export_published_data.py`：本稿で作成したデータのうち株価を用いないものを `data/published/` に書き出す
- `code/02_analysis/`：論文の表・図を1つずつ作る。ファイル名は「表・図の番号＋内容」である。`sample.py` が分析対象の403件を読み込み、全体・部分買付け・張り付いた案件の件数（403・64・187件）が論文と違えば止まる。`equation.py` は回帰式（4.1節：max(S_i, 0)、部分買付け P_i、P_i×max(S_i, 0)、取引条件、年のダミー変数）の変数を定め、回帰の推定もここで行う。張り付きの変数（|S_i|≦1%）は主な式に入れず、付録の頑健性の確認にだけ使う。予測（`table5_prediction_errors.py`）は回帰式の右辺と同じ変数を使い、変数と収益率の関係の形はあらかじめ決めずに学習する。方法は、数値だけのモデルで6つの方法の平均絶対誤差を比べてプログラムが選ぶ（ランダムフォレストが選ばれる）。

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
| 表3.4 取引条件の定義と件数 | `code/01_dataprep/04_extract_deal_terms.py` | `data/processed/deal_terms.csv` | 定義は `data/codebook.csv` |
| 図3.2 取引条件の判定の流れ | `code/02_analysis/figure3_2_how_deal_terms_are_judged.py` | `figure3_2_how_deal_terms_are_judged.png` | |
| 付録A 生成AIの判定との照合 | `code/02_analysis/appendix_a_agreement_with_ai.py` | `appendix_a_agreement_with_ai.csv` | 不一致はすべて原文で確認 |
| 付録A 表A.1 書類から抜き出す箇所 | `code/01_dataprep/00_cut_document_passages.py`、`document_passage_cutting.py` | `data/processed/document_passages/` | |
| 3.3節 買付価格の照合 | `code/01_dataprep/07_check_offer_prices.py` | `offer_price_check.csv` | |
| 図4.1 価格差と収益率の関係（全部買付け・部分買付け） | `code/02_analysis/figure4_1_price_gap_and_return.py` | `figure4_1_price_gap_and_return.png` | |
| 図4.2 収益率の分布と対数変換後の分布 | `code/02_analysis/figure4_2_return_before_and_after_log.py` | `figure4_2_return_before_and_after_log.png` | 歪度も出力する |
| 4.1節の式 | `code/02_analysis/equation.py` | （なし） | 回帰の式。予測も同じ変数を使う |
| 第3・4章の本文中の数値 | `code/02_analysis/numbers_in_text.py` | `numbers_in_text.txt` | |
| 第5章 回帰分析（取引条件を1つずつ加える主表、部分買付けの項、10条件の同時モデルとWald検定、指針後の案件） | `code/02_analysis/table5_regressions.py R1` | `table5_regressions_R1.csv` | 表番号は第5章の執筆後に記す |
| 第5章 予測の方法の選択（数値だけのモデルで6つの方法を比べる） | `code/02_analysis/table5_prediction_errors.py R1` | `table5_method_selection_R1.csv` | 平均絶対誤差が最小の方法を使う |
| 第5章 予測誤差の比較（403件を会社ごとに10グループに分けて評価。平均絶対誤差と二乗平均平方根誤差、95%ブートストラップ区間と Diebold-Mariano 検定） | `code/02_analysis/table5_prediction_errors.py R1` | `table5_prediction_errors_R1.csv`、`table5_prediction_errors_R1_by_deal.csv` | |
| 第5章 市場の注目度 | `code/02_analysis/table5_attention.py` | `table5_attention.csv` | |
| 頑健性：TOPIX を引いた収益 | `table5_regressions.py W1`、`table5_prediction_errors.py W1` | `table5_regressions_W1.csv`、`table5_prediction_errors_W1.csv` | |
| 頑健性：書類の規則の境界にある4件を加える | `table5_regressions.py R1 --include-boundary-deals` | `table5_regressions_R1_including_boundary_deals.csv` | |
| 頑健性（付録）：時間の順に予測する（2024年上期〜2026年上期、221件） | `table5_prediction_errors.py R1 --evaluation time` | `table5_method_selection_R1_time.csv`、`table5_prediction_errors_R1_time.csv` | |
| 頑健性（付録）：張り付きの変数を回帰式に加える | `code/02_analysis/table5_regressions.py R1` | `table5_regressions_R1.csv` の (6) | |
| 頑健性（付録）：張り付きの変数の閾値を0.5・1・2・3%に変える | `code/02_analysis/robustness_thresholds.py` | `robustness_thresholds.csv` | |
| 付録D 表D.1 すべての方法・評価の仕方・張り付きの変数の有無での予測誤差 | `code/02_analysis/tableD1_prediction_errors_by_method.py` | `tableD1_prediction_errors_by_method.csv` | |
| 付録C 直線の価格差 S_i を式に加える | `code/02_analysis/table5_regressions.py R1` | `table5_regressions_R1.csv` の (4) | |
| 付録C 図C.1 全部買付けの価格差の絶対値の分布 | `code/02_analysis/figureC1_absolute_price_gap_distribution.py` | `figureC1_absolute_price_gap_distribution.png` | 張り付きの変数の閾値1%の位置を示す |

## 参考文献

- Gentzkow, M. and J. M. Shapiro (2014) *Code and Data for the Social Sciences: A Practitioner's Guide*.
- Social Science Data Editors, *Template README for Social Science Replication Packages*, https://social-science-data-editors.github.io/template_README/
- Hsieh, J. and R. A. Walkling (2005) "Determinants and Implications of Arbitrage Holdings in Acquisitions," *Journal of Financial Economics* 77(3), 605–648.
