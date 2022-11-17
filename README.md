# Проектное задание: ETL

## Задание спринта

Написать отказоустойчивый перенос данных из Postgres в Elasticsearch

## Особенности реализации

- Предложенная [cхему индекса](https://code.s3.yandex.net/middle-python/learning-materials/es_schema.txt)💾  `movies`, 
  была перенесена в файл `movies.json`. За создание и конфигурирование индекса ElasticSearch отвечает класс 
  `EtlProcess`. Такой json-файл должен быть создан и находится в папке `config` для каждого индекса в который данные
  загружаются посредством этого ETL.
- ETL позволяет гибко настроить автоматическую загрузку данных из нескольких таблиц SQL в несколько индексов 
  ElasticSearch. Для каждого индекса в файле `config/settings.toml` устанавливаются связи с таблица SQL базы данных.
  Эти таблицы в конфигурационном файле могут быть связаны связями 1-к-1, один ко многим, многие ко многим. За счет этого
  система легко масштабируется. В итоговой выборке, которая получена через сгенерированный автоматически запрос,
  данные могут быть сгруппированы в JSON-структуры и массивы.
- При запуске ETL проверяет нет ли процессов python с таким же именем скрипта.
- Проект корректно отрабатывает падение PosgtresSQL, Radis, ElasticSearch.

### Связи между индексом ElasticSearch и таблицами SQL в конфиг. файле: 
```
"bindings_elastic_to_sql": [
      ..., # Связанных индексов и таблиц может быть несколько
      {
         "elastic_index": "movies", # Имя индекса
         "transform_class": "MoviesDataTransform", # Имя класса в файле etl_data_transform.py, отвечающего за трансформ. данных.
         "mapping_file": "es_movies.json", # Имя файла в текущей папки из которого должен быть сконфигурирован индекс. 
         "table": { # Основная таблица SQL базы данных
            "name": "film_work",
            "alias": "fw",
            "fields": [ 
                # Поля, которые попадут в выборку
               "id",
               "title",
               "description",
               "rating",
               "modified"
            ],
            "aliases": {
               # Псевдоними для полей таблиц, чтобы упросить трансформацию данных.
               "rating": "imdb_rating"
            },
            "field_actual_state_name": "modified", # Поле по которому отслеживается изменение записей.
            "children": [ # Связанные с основной таблицей таблицы. Поддерживает вложенность 2 для связей многие-ко-многим.
               {
                  "name": "genre_film_work",
                  "alias": "gfw",
                  "group": "genre", # Данные будут сгруппированы, если в группировке одно поле - будет массив, несколько - JSON.
                  "join": {
                     "film_work_id": "id" # Поле дочерней табицы: Поле родительской таблицы по которым делается JOIN.
                  },
                  "children": [
                     {
                        "name": "genre",
                        "alias": "gr",
                        "join": {
                           "id": "genre_id"
                        },
                        "fields": [
                           "name"
                        ],
                        "field_actual_state_name": "modified"
                     }
                  ]
               },
               {
                  "name": "person_film_work",
                  "alias": "pfw",
                  "group": "persons",
                  "fields": [
                     "role"
                  ],
                  "join": {
                     "film_work_id": "id"
                  },
                  "children": [
                     {
                        "name": "person",
                        "alias": "pn",
                        "join": {
                           "id": "person_id"
                        },
                        "fields": [
                           "id",
                           "full_name",
                           "modified"
                        ],
                        "aliases": {
                           "full_name": "name"
                        },
                        "field_actual_state_name": "modified"
                     }
                  ]
               }
            ]
         }
      }
   ]
```

### Пример SQL-запроса, генерируемого автоматически ETL на основании конфиг. файла:
```
SELECT 
 "fw"."id" AS "id",
 "fw"."title" AS "title",
 "fw"."description" AS "description",
 "fw"."rating" AS "imdb_rating",
 "fw"."modified" AS "modified",
 array_agg (DISTINCT "gr"."name") AS "genre",
 COALESCE (json_agg(DISTINCT jsonb_build_object(
  'role', "pfw"."role", 
  'id', "pn"."id", 
  'name', "pn"."full_name", 
  'modified', "pn"."modified"
)) FILTER (WHERE "pn"."modified" is not null), '[]') AS "persons",
 "_tracked_table"."_tracked_field" 
FROM "content"."film_work" AS "fw"
LEFT JOIN "content"."genre_film_work" AS "gfw" ON "fw"."id" = "gfw"."film_work_id"
LEFT JOIN "content"."genre" AS "gr" ON "gfw"."genre_id" = "gr"."id"
LEFT JOIN "content"."person_film_work" AS "pfw" ON "fw"."id" = "pfw"."film_work_id"
LEFT JOIN "content"."person" AS "pn" ON "pfw"."person_id" = "pn"."id"
JOIN (
  SELECT "fw"."id" AS "id", pn.modified AS "_tracked_field"
  FROM "content"."film_work" AS "fw"
  JOIN "content"."person_film_work" AS "pfw" ON "fw"."id" = "pfw"."film_work_id"
  JOIN "content"."person" AS "pn" ON "pfw"."person_id" = "pn"."id"
  WHERE pn.modified > %s 
  ORDER BY pn.modified
  LIMIT 10000 OFFSET %s
  ) AS "_tracked_table" ON ""fw"."id"" = "_tracked_table"."id" 
GROUP BY
 "fw"."id",
 "fw"."title",
 "fw"."description",
 "fw"."rating",
 "fw"."modified",
 "_tracked_table"."_tracked_field"
LIMIT 10000
```

P.S. Кода много получилось, не очень чительно, мне кажется. Буду благодарен комментариям)