import os.path
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://link.springer.com"
PAGE_PARAMS = (
    "?showAll=true&package=mat-covid19_textbooks"
    "&facet-content-type=%22Book%22&sortOrder=newestFirst"
)


class Formatter:
    def __init__(self, url_modifier: str, extension: str):
        self.url_modifier = url_modifier
        self.extension = extension


# Available formats
class Formats:
    pdf = Formatter("content/pdf/", "pdf")
    epub = Formatter("download/epub/", "epub")


class Book:

    windows_bad_chars = r"\/:*?<>|"

    def __init__(self, title: str, href: str, formatter: Formatter):
        self._title = self._clean_title(title)
        self._href = href
        self._formatter = formatter

    def _clean_title(self, title: str):
        title = title.strip()
        for c in self.windows_bad_chars:
            title = title.replace(c, "")
        return title

    @property
    def title(self):
        return self._title

    @property
    def file_name(self):
        return f"{self._title}.{self._formatter.extension}"

    @property
    def download_url(self):
        change = self._href.replace("book/", self._formatter.url_modifier)
        return f"{BASE_URL}{change}.{self._formatter.extension}"

    def __str__(self):
        return self.title


class BooksDownloader:
    def __init__(self, folder, overwrite=False):
        self._folder = folder
        self._overwrite = overwrite
        Path(self._folder).mkdir(exist_ok=True)

    @property
    def folder(self):
        return self._folder

    def get_book(self, book):
        file_path = os.path.join(self._folder, book.file_name)
        if os.path.isfile(file_path) and not self._overwrite:
            print(f"Already found {book.title} in folder, skipping...")
            return

        print(f"Attempting to download <<{book.title}>> ...")
        with requests.get(book.download_url, stream=True) as r:
            r.raise_for_status()
            with open(file_path, "wb") as f:
                print(f"Saving to <<{file_path}>>")
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"<<{book.title}>> downloaded!")

    def flush_unfinished_book(self, book):
        file_path = os.path.join(self._folder, book.file_name)
        os.remove(file_path)
        print(f"<<{file_path}>> deleted.")


def get_page(number: int) -> BeautifulSoup:

    print(f"Fetching page {number}")

    page_url = f"{BASE_URL}/search/page/{number}{PAGE_PARAMS}"
    response = requests.get(page_url)

    if response.status_code == 200:
        page = response.content
        soup = BeautifulSoup(page, features="html.parser")
        return soup

    else:
        print(f"Request on page {page} FAILED!")


def get_books_from_page(page: BeautifulSoup, file_format: Formatter) -> List[Book]:
    items = page.find_all("a", {"class": "title"})
    return [Book(item.text, item["href"], file_format) for item in items]


def main():

    # Config (Modify if you want)
    download_folder = "books"
    overwrite_files = False
    file_format = Formats.pdf  # also works for epub
    start, end = 1, 24  # pages to fetch (source pagination)

    # Instantiate downloader
    downloader = BooksDownloader(download_folder, overwrite=overwrite_files)

    # Get pages 1 to 24
    for page_number in range(start, end + 1):
        page = get_page(page_number)
        books = get_books_from_page(page, file_format)
        for book in books:
            try:
                downloader.get_book(book)
            except KeyboardInterrupt:
                print("(!) Script terminating...")
                downloader.flush_unfinished_book(book)
                exit("(!) Exit forced")


if __name__ == "__main__":
    main()
