import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

csv_file = "demo.csv"
output_csv_file = f"{csv_file}_output.csv"
df = pd.read_csv(csv_file)


def scrape_journal_info(row):
    maintitle, title, issn, pubyear = (
        row["Title"],
        row["Publication Title"],
        row["ISSN"],
        row["Publication Year"],
    )
    base_url = "https://www.scimagojr.com/journalsearch.php"
    search_url = f"{base_url}?q={issn}"
    h_index, latest_q_ranking = None, None

    try:
        response = requests.get(search_url)
        soup = BeautifulSoup(response.content, "html.parser")

        pagination_text = soup.find("div", class_="pagination")
        if pagination_text and "of" in pagination_text.text:
            total_results = int(pagination_text.text.strip().split("of")[-1].strip())
            if total_results == 1:
                result = soup.find("div", class_="search_results").find("a")
                journal_url = f"{base_url}{result['href']}"
                response = requests.get(journal_url)
                journal_soup = BeautifulSoup(response.content, "html.parser")
                h_index_element = journal_soup.find("p", class_="hindexnumber")
                if h_index_element:
                    h_index = h_index_element.text.strip()

                cellcontent_div = journal_soup.find("div", class_="cellcontent")
                if cellcontent_div:
                    quartiles_div = cellcontent_div.find_all("div", class_="cellslide")[
                        1
                    ]
                    rows = quartiles_div.find_all("tr")[1:]
                    if rows:
                        latest_row = rows[-1]
                        cells = latest_row.find_all("td")
                        if len(cells) == 3:
                            latest_q_ranking = cells[-1].text.strip()
    except Exception as e:
        print(f"Failed to scrape ISSN {issn}: {e}")
        return title, issn, None, None

    return maintitle, title, issn, h_index, latest_q_ranking, pubyear


results = []
with ThreadPoolExecutor(max_workers=8) as executor:
    future_to_issn = {
        executor.submit(scrape_journal_info, row): row for index, row in df.iterrows()
    }

    for future in as_completed(future_to_issn):
        result = future.result()
        if result[2] is not None:
            results.append(result)

output_df = pd.DataFrame(
    results,
    columns=["Title", "Publication Title", "ISSN", "h-index", "q-ranking", "Year"],
)
output_df.to_csv(output_csv_file, index=False, sep=";")

print(f"Data saved to {output_csv_file}")
