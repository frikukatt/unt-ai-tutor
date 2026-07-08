from app.data import Academic_majors, Creative_majors

all_majors = Academic_majors + Creative_majors


def search_by_name(name: str):
    result = []

    for major in all_majors:
        if name.lower() in major["name"].lower():
            result.append(major)

    return result