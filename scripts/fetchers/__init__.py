"""
Fetchers module untuk berbagai sumber data.

Setiap fetcher harus memiliki fungsi fetch(source: dict) -> Set[str]
yang mengembalikan set of strings (IP addresses atau domains).
"""
