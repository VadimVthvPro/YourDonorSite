#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сбора медицинских учреждений Беларуси из OpenStreetMap.
Результат сохраняется в JSON-файл для использования на сайте.

Установите зависимости перед запуском:
pip install osmnx geopandas shapely reverse_geocoder tqdm

Запуск:
python build_medical_json.py
"""

import osmnx as ox
import geopandas as gpd
import reverse_geocoder as rg
from collections import defaultdict
from tqdm import tqdm
import json
import re

# Маппинг английских названий на русские
REGION_TRANSLATION = {
    "Minsk Region": "Минская область",
    "Minsk City": "город Минск",
    "Brest Region": "Брестская область",
    "Gomel Region": "Гомельская область",
    "Grodno Region": "Гродненская область",
    "Vitebsk Region": "Витебская область",
    "Mogilev Region": "Могилёвская область",
}

# Маппинг районов
DISTRICT_TRANSLATION = {
    "Minsk District": "Минский район",
    "Brest District": "Брестский район",
    "Gomel District": "Гомельский район",
    "Grodno District": "Гродненский район",
    "Vitebsk District": "Витебский район",
    "Mogilev District": "Могилёвский район",
    "Baranovichi District": "Барановичский район",
    "Borisov District": "Борисовский район",
    "Bobruisk District": "Бобруйский район",
    "Pinsk District": "Пинский район",
    "Orsha District": "Оршанский район",
    "Lida District": "Лидский район",
    "Mozyr District": "Мозырский район",
    "Soligorsk District": "Солигорский район",
    "Novopolotsk District": "Новополоцкий район",
    "Polotsk District": "Полоцкий район",
    "Svetlogorsk District": "Светлогорский район",
    "Zhlobin District": "Жлобинский район",
    "Rechitsa District": "Речицкий район",
    "Slutsk District": "Слуцкий район",
    "Molodechno District": "Молодечненский район",
    "Zhodino District": "Жодинский район",
}

def translate_region(name):
    """Перевод названия области на русский"""
    return REGION_TRANSLATION.get(name, name)

def translate_district(name):
    """Перевод названия района на русский"""
    if name in DISTRICT_TRANSLATION:
        return DISTRICT_TRANSLATION[name]
    # Попробуем автоматически русифицировать
    return name

def clean_name(name):
    """Очистка и нормализация названия учреждения"""
    if not name:
        return None
    # Убираем лишние пробелы
    name = re.sub(r'\s+', ' ', name.strip())
    return name

def main():
    print("=" * 60)
    print("Сбор медицинских учреждений Беларуси из OpenStreetMap")
    print("=" * 60)
    
    print("\n🌍 Загружаем границы Беларуси...")
    try:
        country = ox.geocode_to_gdf("Belarus")
    except Exception as e:
        print(f"❌ Ошибка загрузки границ: {e}")
        return

    # Теги для поиска медицинских учреждений
    TAGS = {
        "amenity": ["hospital", "clinic", "doctors"],
        "healthcare": ["hospital", "clinic", "polyclinic"]
    }

    print("🏥 Загружаем объекты медицины из OpenStreetMap...")
    try:
        gdf = ox.features_from_polygon(country.geometry.iloc[0], TAGS)
    except Exception as e:
        print(f"❌ Ошибка загрузки объектов: {e}")
        return

    # Фильтруем объекты с геометрией
    gdf = gdf[gdf.geometry.notnull()].copy()
    gdf["lat"] = gdf.geometry.centroid.y
    gdf["lon"] = gdf.geometry.centroid.x

    print(f"📊 Найдено объектов: {len(gdf)}")

    # Получаем координаты для обратного геокодирования
    coords = list(zip(gdf["lat"], gdf["lon"]))
    print("📍 Определяем регионы и районы...")
    geo_results = rg.search(coords)

    # Структура для результата
    result = defaultdict(lambda: defaultdict(list))
    
    # Счётчики для статистики
    stats = {
        "hospital": 0,
        "clinic": 0,
        "polyclinic": 0,
        "doctors": 0,
        "other": 0
    }

    print("🔄 Обрабатываем данные...")
    for idx, row in tqdm(gdf.iterrows(), total=len(gdf)):
        geo = geo_results[list(gdf.index).index(idx)]
        
        # Получаем и переводим регион и район
        region = translate_region(geo.get("admin1", "Неизвестная область"))
        district = translate_district(geo.get("admin2", "Неизвестный район"))
        
        # Получаем название
        name = clean_name(row.get("name"))
        if not name:
            continue

        # Определяем тип учреждения
        obj_type = (
            row.get("healthcare")
            or row.get("amenity")
            or "medical"
        )
        
        # Обновляем статистику
        if obj_type in stats:
            stats[obj_type] += 1
        else:
            stats["other"] += 1

        # Создаём запись
        entry = {
            "id": f"{region[:3]}_{district[:3]}_{len(result[region][district])+1}".lower().replace(" ", "_"),
            "name": name,
            "type": obj_type,
            "lat": round(row["lat"], 6),
            "lon": round(row["lon"], 6)
        }

        # Проверяем на дубликаты по названию
        existing_names = [item["name"] for item in result[region][district]]
        if name not in existing_names:
            result[region][district].append(entry)

    # Сортируем учреждения по алфавиту внутри каждого района
    for region in result:
        for district in result[region]:
            result[region][district].sort(key=lambda x: x["name"])

    # Конвертируем в обычный словарь
    final_data = {
        "metadata": {
            "source": "OpenStreetMap",
            "country": "Belarus",
            "generated": True
        },
        "regions": {region: dict(districts) for region, districts in result.items()}
    }

    # Сохраняем результат
    output_file = "../data/medcenters.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    # Выводим статистику
    print("\n" + "=" * 60)
    print("✅ Готово!")
    print("=" * 60)
    print(f"\n📁 Файл сохранён: {output_file}")
    print(f"📊 Количество областей: {len(final_data['regions'])}")
    
    total_districts = sum(len(districts) for districts in final_data['regions'].values())
    print(f"📊 Количество районов: {total_districts}")
    
    total_objects = sum(
        len(items) 
        for districts in final_data['regions'].values() 
        for items in districts.values()
    )
    print(f"📊 Всего учреждений: {total_objects}")
    
    print("\n📈 По типам:")
    for obj_type, count in stats.items():
        if count > 0:
            print(f"   {obj_type}: {count}")

if __name__ == "__main__":
    main()
