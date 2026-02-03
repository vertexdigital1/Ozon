import requests
import json
from datetime import datetime
import pandas as pd
import os


def get_credentials():
    """
    Запрос учетных данных у пользователя
    """
    print("=" * 50)
    print("ВВЕДИТЕ УЧЕТНЫЕ ДАННЫЕ OZON API")
    print("=" * 50)

    print("\nГде взять учетные данные:")
    print("1. Зайдите в личный кабинет OZON Seller")
    print("2. Перейдите в раздел Настройки → Ключи API")
    print("3. Скопируйте Client-ID и API Key")
    print("=" * 50)

    # Запрос Client ID
    client_id = input("\nВведите Client-ID: ").strip()
    while not client_id:
        print("❌ Client-ID не может быть пустым!")
        client_id = input("Введите Client-ID: ").strip()

    # Запрос API Key (без скрытия ввода)
    api_key = input("\nВведите API Key: ").strip()
    while not api_key:
        print("❌ API Key не может быть пустым!")
        api_key = input("API Key: ").strip()

    return client_id, api_key


def get_ozon_stock(client_id, api_key, limit=1000, offset=0):
    """
    Получение остатков по складам OZON (только FBO)
    """
    url = "https://api-seller.ozon.ru/v2/analytics/stock_on_warehouses"

    headers = {
        "Client-Id": str(client_id),
        "Api-Key": str(api_key),
        "Content-Type": "application/json",
    }

    payload = {
        "limit": limit,
        "offset": offset,
        "warehouse_type": "FBO",  # Только FBO склады
    }

    try:
        print(f"📡 Отправка запроса с limit={limit}, offset={offset}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}
        else:
            return {
                "success": False,
                "error": f"Ошибка API: {response.status_code}",
                "details": response.text[:500],
            }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Ошибка соединения: {str(e)}"}


def get_all_stock_paginated(client_id, api_key):
    """
    Получение всех данных с пагинацией
    """
    all_items = []
    limit = 1000
    offset = 0

    print("\n" + "=" * 50)
    print("НАЧАЛО ЗАГРУЗКИ ДАННЫХ")
    print("=" * 50)

    while True:
        print(f"\n📄 Страница {offset//limit + 1} (offset: {offset})")

        result = get_ozon_stock(
            client_id=client_id, api_key=api_key, limit=limit, offset=offset
        )

        if not result["success"]:
            print(f"❌ Ошибка: {result.get('error')}")
            if "details" in result:
                print(f"Подробности: {result['details']}")
            break

        data = result["data"]
        rows = data.get("result", {}).get("rows", [])

        if not rows:
            print("✓ Нет данных для загрузки")
            break

        # Преобразуем данные, извлекаем нужные поля
        processed_rows = []
        for item in rows:
            processed_item = {
                "product_name": item.get("product_name") or item.get("item_name") or "",
                "offer_id": item.get("offer_id") or item.get("item_code") or "",
                "sku": item.get("sku") or "",
                "warehouse_name": item.get("warehouse_name") or "",
                "free_to_sell_amount": item.get("free_to_sell_amount")
                or item.get("quantity")
                or 0,
                "reserved": item.get("reserved") or item.get("reserved_quantity") or 0,
                "promised_amount": item.get("promised_amount")
                or item.get("promised")
                or 0,
            }
            processed_rows.append(processed_item)

        all_items.extend(processed_rows)
        print(f"✓ Загружено записей: {len(rows)}")
        print(f"✓ Всего загружено: {len(all_items)}")

        # Показываем пример данных из первой страницы
        if offset == 0 and processed_rows:
            print("\n📋 Пример данных с первой страницы:")
            for i, item in enumerate(processed_rows[:2], 1):
                print(f"  {i}. Название: {item.get('product_name', 'Нет')}")
                print(f"     Артикул: {item.get('offer_id', 'Нет')}")
                print(f"     SKU: {item.get('sku', 'Нет')}")
                print(f"     Склад: {item.get('warehouse_name', 'Нет')}")
                print(f"     Доступно: {item.get('free_to_sell_amount')}")

        # Если получено меньше записей, чем лимит - это последняя страница
        if len(rows) < limit:
            print("✓ Последняя страница достигнута")
            break

        # Переходим к следующей странице
        offset += limit

        # Защита от бесконечного цикла
        if offset > 50000:
            print("⚠️  Достигнут максимальный лимит смещения")
            break

    return all_items


def analyze_stock_data(data):
    """Анализ полученных данных"""
    if not data:
        print("❌ Нет данных для анализа")
        return

    print("\n" + "=" * 50)
    print("АНАЛИЗ ДАННЫХ")
    print("=" * 50)
    print(f"📊 Всего записей: {len(data)}")

    # Общая статистика
    total_quantity = 0
    total_reserved = 0
    total_promised = 0
    warehouses = {}

    for item in data:
        quantity = item.get("free_to_sell_amount", 0)
        reserved = item.get("reserved", 0)
        promised = item.get("promised_amount", 0)

        total_quantity += quantity
        total_reserved += reserved
        total_promised += promised

        warehouse = item.get("warehouse_name", "Неизвестный склад")
        if warehouse not in warehouses:
            warehouses[warehouse] = {"quantity": 0, "reserved": 0, "promised": 0}
        warehouses[warehouse]["quantity"] += quantity
        warehouses[warehouse]["reserved"] += reserved
        warehouses[warehouse]["promised"] += promised

    print(f"📦 Общее количество товаров: {total_quantity:,} шт.".replace(",", " "))
    print(f"🔒 Всего в резерве: {total_reserved:,} шт.".replace(",", " "))
    print(f"📝 Всего обещано: {total_promised:,} шт.".replace(",", " "))
    print(f"🏭 Уникальных складов: {len(warehouses)}")

    # Проверяем наличие данных в полях
    print("\n📊 Проверка заполненности полей:")
    total_items = len(data)
    fields_to_check = ["product_name", "offer_id", "sku", "warehouse_name"]
    for field in fields_to_check:
        filled = sum(
            1 for item in data if item.get(field) and str(item.get(field)).strip()
        )
        percentage = (filled / total_items) * 100 if total_items > 0 else 0
        print(f"  • {field}: {filled}/{total_items} ({percentage:.1f}%)")

    # Топ 5 складов
    if warehouses:
        print("\n🏆 ТОП 5 СКЛАДОВ:")
        sorted_warehouses = sorted(
            warehouses.items(), key=lambda x: x[1]["quantity"], reverse=True
        )[:5]
        for i, (warehouse, stats) in enumerate(sorted_warehouses, 1):
            print(f"  {i}. {warehouse}:")
            print(f"     Доступно: {stats['quantity']:,} шт.".replace(",", " "))
            print(f"     Резерв: {stats['reserved']:,} шт.".replace(",", " "))
            print(f"     Обещано: {stats['promised']:,} шт.".replace(",", " "))


def export_to_excel(data, filename=None):
    """
    Экспорт данных в Excel файл
    """
    if not data:
        print("❌ Нет данных для экспорта")
        return None

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ozon_stock_FBO_{timestamp}.xlsx"

    try:
        # Создаем DataFrame с правильным порядком столбцов
        df = pd.DataFrame(
            data,
            columns=[
                "product_name",  # Item name (название)
                "offer_id",  # Item code (артикул)
                "sku",  # SKU
                "warehouse_name",  # Склад
                "free_to_sell_amount",  # Количество доступное для продажи
                "reserved",  # Reserved (резерв)
                "promised_amount",  # Promised amount
            ],
        )

        # Заменяем пустые значения на "Нет данных"
        df.fillna(
            {
                "product_name": "Нет данных",
                "offer_id": "Нет данных",
                "sku": "Нет данных",
                "warehouse_name": "Неизвестный склад",
            },
            inplace=True,
        )

        # Преобразуем числовые колонки в нужный тип
        numeric_columns = ["free_to_sell_amount", "reserved", "promised_amount"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Настройка ширины колонок
        column_widths = {
            "product_name": 40,
            "offer_id": 20,
            "sku": 15,
            "warehouse_name": 30,
            "free_to_sell_amount": 15,
            "reserved": 15,
            "promised_amount": 15,
        }

        # Сохраняем в Excel с настройками
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Остатки FBO", index=False)

            # Получаем объект workbook и worksheet для настройки
            workbook = writer.book
            worksheet = writer.sheets["Остатки FBO"]

            # Устанавливаем ширину колонок
            for col_letter, col_name in zip("ABCDEFG", df.columns):
                worksheet.column_dimensions[col_letter].width = column_widths.get(
                    col_name, 15
                )

            # Заголовки жирным шрифтом
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)

        print(f"✓ Данные сохранены в Excel файл: {filename}")
        print(f"📊 Количество строк: {len(df)}")

        # Показываем структуру файла
        print("\n📁 Структура файла Excel:")
        print("  A: Item name (название)")
        print("  B: Item code (артикул)")
        print("  C: SKU")
        print("  D: Склад")
        print("  E: Количество доступное для продажи")
        print("  F: Reserved (резерв)")
        print("  G: Promised amount")

        return filename

    except Exception as e:
        print(f"❌ Ошибка при сохранении в Excel: {e}")
        return None


def test_connection(client_id, api_key):
    """
    Тестирование подключения к API
    """
    print("\n🔍 Тестирование подключения к OZON API...")

    result = get_ozon_stock(client_id=client_id, api_key=api_key, limit=1, offset=0)

    if result["success"]:
        print("✅ Подключение успешно!")
        return True
    else:
        print(f"❌ Ошибка подключения: {result.get('error')}")
        return False


def main():
    """
    Основная функция
    """
    print("\n" + "=" * 60)
    print("OZON FBO СКЛАДЫ - ПОЛУЧЕНИЕ ОСТАТКОВ ПО API")
    print("=" * 60)
    print("ℹ️  Загружаются данные только с FBO складов")
    print("=" * 60)

    # Получаем учетные данные
    client_id, api_key = get_credentials()

    # Тестируем подключение
    if not test_connection(client_id, api_key):
        print("\n❌ Не удалось подключиться. Проверьте:")
        print("1. Правильность Client-ID и API Key")
        print("2. Наличие доступа к API")
        print("3. Интернет-соединение")
        return

    # Запрос на полную загрузку
    print("\n" + "=" * 50)
    full_load = input("\nЗагрузить ВСЕ данные? (да/нет): ").lower().strip()

    if full_load not in ["да", "д", "yes", "y"]:
        print("\n👋 Работа завершена")
        return

    # Полная загрузка данных
    print("\n" + "=" * 50)
    print("ПОЛНАЯ ЗАГРУЗКА ДАННЫХ")
    print("=" * 50)

    all_data = get_all_stock_paginated(client_id, api_key)

    if not all_data:
        print("❌ Не удалось загрузить данные")
        return

    # Анализ данных
    analyze_stock_data(all_data)

    # Экспорт данных в Excel
    print("\n" + "=" * 50)
    export = input("\nЭкспортировать данные в Excel? (да/нет): ").lower().strip()

    if export in ["да", "д", "yes", "y"]:
        filename = export_to_excel(all_data)
        if filename:
            print(f"\n✅ Экспорт завершен!")
            print(f"📁 Файл: {os.path.abspath(filename)}")
            print(f"📊 Записей: {len(all_data)}")

            # Предложение открыть файл
            open_file = input("\nОткрыть файл? (да/нет): ").lower().strip()
            if open_file in ["да", "д", "yes", "y"]:
                try:
                    os.startfile(filename)  # Для Windows
                except:
                    print("⚠️  Не удалось открыть файл автоматически")

    print("\n" + "=" * 50)
    print("✅ ПРОГРАММА УСПЕШНО ЗАВЕРШЕНА")
    print("=" * 50)


if __name__ == "__main__":
    try:
        # Проверяем наличие необходимых библиотек
        try:
            import pandas as pd
            import openpyxl
        except ImportError as e:
            print(f"❌ Отсутствуют необходимые библиотеки: {e}")
            print("Установите их командой: pip install pandas openpyxl")
            input("\nНажмите Enter для выхода...")
            exit()

        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
    finally:
        input("\nНажмите Enter для выхода...")
