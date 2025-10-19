def tags_sort(tag):
    str_tag = str(tag)

    if str_tag in ("identify", "extension"):
        return "a" + str_tag

    if str_tag in ("journal", "map feature"):
        return "b" + str_tag

    if str_tag.startswith("time"):
        return "c" + str_tag

    if str_tag.startswith("coords"):
        return "d" + str_tag

    return "z" + str_tag
