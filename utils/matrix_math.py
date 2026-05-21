def reduce_arcana(num: int) -> int:
    """
    Зменшує число до <= 22 за правилами Матриці Долі (шляхом додавання цифр).
    Якщо після першого додавання число все ще > 22, воно додається знову.
    """
    while num > 22:
        num = sum(int(d) for d in str(num))
    
    # У Матриці Долі нульового аркану немає, число 0 зазвичай трактується як 22 (Блазень)
    return num if num > 0 else 22


def calculate_matrix(date_str: str) -> dict[str, int]:
    """
    Приймає дату у форматі DD.MM.YYYY і повертає базові 4 точки Матриці.
    
    Згідно з техзавданням:
    - Портрет: день народження.
    - Талант: місяць народження.
    - Кармічний хвіст (Минуле): сума цифр року народження.
    - Центр (Характер): сума Портрету, Таланту та Кармічного хвоста.
    """
    parts = date_str.split('.')
    day = int(parts[0])
    month = int(parts[1])
    year_str = parts[2]

    portrait = reduce_arcana(day)
    talent = reduce_arcana(month)
    
    year_sum = sum(int(digit) for digit in year_str)
    karma = reduce_arcana(year_sum)
    
    center = reduce_arcana(portrait + talent + karma)

    return {
        "portrait": portrait,
        "talent": talent,
        "karma": karma,
        "center": center
    }
