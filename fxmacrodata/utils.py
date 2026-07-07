def sort_by_date(data_list):
    """Sorts a list of indicator data dictionaries by 'date' or 'release_date'."""
    return sorted(data_list, key=lambda x: x.get("date") or x.get("release_date"))
