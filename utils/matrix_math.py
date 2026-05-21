def reduce_arcana(num: int) -> int:
    """
    Зменшує число за класичним правилом Матриці Долі (метод 22 Арканів).
    Якщо число > 22, додаємо його цифри, поки не отримаємо число <= 22.
    """
    if num == 0:
        return 22
    
    while num > 22:
        num = sum(int(d) for d in str(num))
        
    return num


def calculate_matrix(date_str: str) -> dict[str, int]:
    """
    Приймає дату DD.MM.YYYY.
    Розраховує 5 головних точок ОСОБИСТОГО хреста Матриці Долі.
    """
    try:
        parts = date_str.split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
    except (ValueError, IndexError):
        return {} # Валідація на випадок збою форми

    # 1. Ліва точка (Захід) — Точка особистості, візитівка
    left_point = reduce_arcana(day)
    
    # 2. Верхня точка (Північ) — Зв'язок з Ангелом-Охоронцем, таланти
    top_point = reduce_arcana(month)
    
    # 3. Права точка (Схід) — Матеріальне прагнення, соціум (Рік)
    right_point = reduce_arcana(year)
    
    # 4. Нижня точка (Південь) — Кармічний хвіст (Минулі життя, головний блок)
    # Рахується як сума трьох попередніх точок
    bottom_point = reduce_arcana(left_point + top_point + right_point)
    
    # 5. Центр (Зона комфорту, Характер, суть душі)
    # Рахується як сума всіх 4 крайніх точок хреста
    center_point = reduce_arcana(left_point + top_point + right_point + bottom_point)

    return {
        "portrait": left_point,    # День (Ліво)
        "talent": top_point,       # Місяць (Вгорі)
        "social": right_point,     # Рік (Право)
        "karma": bottom_point,     # Кармічний хвіст (Внизу)
        "center": center_point     # Характер (Центр)
    }
