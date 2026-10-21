"""Catalogo de especies frutales disponibles en Agro-Colab.

Cada especie tiene un set curado de imagenes (fruta o arbol) que el agricultor
debe elegir al publicar. El backend valida que la imagen usada pertenezca
realmente a la especie declarada, de modo que el catalogo nunca muestre
fotos ajenas al arbol publicado.

Las imagenes provienen de Wikimedia Commons bajo licencias libres (CC BY / CC BY-SA /
dominio publico). Cada foto conserva su atribucion: autor, licencia y enlace de origen.
"""

from typing import Optional

CATALOGO_ESPECIES = [
    {
        "id": "palto_hass",
        "nombre": "Palto Hass",
        "emoji": "🥑",
        "descripcion": "Aguacate variedad Hass, la más plantada en Chile.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Avocado_Pear_fruit_hanging_on_a_pear_plant.jpg/960px-Avocado_Pear_fruit_hanging_on_a_pear_plant.jpg",
                "titulo": "Avocado Pear fruit hanging on a pear plant.jpg",
                "autor": "Treysam",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Avocado_Pear_fruit_hanging_on_a_pear_plant.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Persea_americana_fruits.JPG/960px-Persea_americana_fruits.JPG",
                "titulo": "Persea americana fruits.JPG",
                "autor": "B.navez",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Persea_americana_fruits.JPG",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Secretary_Perdue_meet_CA_Avocado_Comm_at_Rancho_Guejito_Avocado_Farm_%2820190715-OSEC-LSC-1084%29.jpg/960px-Secretary_Perdue_meet_CA_Avocado_Comm_at_Rancho_Guejito_Avocado_Farm_%2820190715-OSEC-LSC-1084%29.jpg",
                "titulo": "Secretary Perdue meet CA Avocado Comm at Rancho Guejito Avocado Farm (20190715-OSEC-LSC-1084).jpg",
                "autor": "USDAgov",
                "licencia": "Public domain",
                "fuente": "https://commons.wikimedia.org/wiki/File:Secretary_Perdue_meet_CA_Avocado_Comm_at_Rancho_Guejito_Avocado_Farm_(20190715-OSEC-LSC-1084).jpg",
            },
        ],
    },
    {
        "id": "naranjo_valencia",
        "nombre": "Naranjo Valencia",
        "emoji": "🍊",
        "descripcion": "Naranja de temporada tardia, muy dulce y aromatica.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Orange_Garden_in_Sittong%2C_Darjeeling.jpg/960px-Orange_Garden_in_Sittong%2C_Darjeeling.jpg",
                "titulo": "Orange Garden in Sittong, Darjeeling.jpg",
                "autor": "Auli Raha (অলি রাহা)",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Orange_Garden_in_Sittong,_Darjeeling.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Oranges_-_whole-halved-segment.jpg/960px-Oranges_-_whole-halved-segment.jpg",
                "titulo": "Oranges - whole-halved-segment.jpg",
                "autor": "Ivar Leidus",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Oranges_-_whole-halved-segment.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Orange_orchard%2C_Karaisal%C4%B1_01.JPG/960px-Orange_orchard%2C_Karaisal%C4%B1_01.JPG",
                "titulo": "Orange orchard, Karaisalı 01.JPG",
                "autor": "Zeynel Cebeci",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Orange_orchard,_Karaisal%C4%B1_01.JPG",
            },
        ],
    },
    {
        "id": "limonero_eureka",
        "nombre": "Limonero Eureka",
        "emoji": "🍋",
        "descripcion": "Limón de piel gruesa, ideal para jugo y uso culinario.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Lemon%2C_Lemon_tree%2C_Florence%2C_Italy.jpg/960px-Lemon%2C_Lemon_tree%2C_Florence%2C_Italy.jpg",
                "titulo": "Lemon, Lemon tree, Florence, Italy.jpg",
                "autor": "Vyacheslav Argenberg",
                "licencia": "CC BY 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Lemon,_Lemon_tree,_Florence,_Italy.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Lemon.jpg/960px-Lemon.jpg",
                "titulo": "Lemon.jpg",
                "autor": "André Karwath aka Aka",
                "licencia": "CC BY-SA 2.5",
                "fuente": "https://commons.wikimedia.org/wiki/File:Lemon.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Limoni_Sul_Garda_-_panoramio.jpg/960px-Limoni_Sul_Garda_-_panoramio.jpg",
                "titulo": "Limoni Sul Garda - panoramio.jpg",
                "autor": "*fiedler*",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Limoni_Sul_Garda_-_panoramio.jpg",
            },
        ],
    },
    {
        "id": "mandarino",
        "nombre": "Mandarino",
        "emoji": "🟠",
        "descripcion": "Mandarino de piel suelta, dulce y fácil de pelar.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Mandarin_Oranges_%28Citrus_Reticulata%29.jpg/960px-Mandarin_Oranges_%28Citrus_Reticulata%29.jpg",
                "titulo": "Mandarin Oranges (Citrus Reticulata).jpg",
                "autor": "Joe Ravi",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Mandarin_Oranges_(Citrus_Reticulata).jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Mandarins_-_whole_and_halved.jpg/960px-Mandarins_-_whole_and_halved.jpg",
                "titulo": "Mandarins - whole and halved.jpg",
                "autor": "Ivar Leidus",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Mandarins_-_whole_and_halved.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Citrus_x_sinensis_Temple_2zz.jpg/960px-Citrus_x_sinensis_Temple_2zz.jpg",
                "titulo": "Citrus x sinensis Temple 2zz.jpg",
                "autor": "Photo by David J. Stang",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Citrus_x_sinensis_Temple_2zz.jpg",
            },
        ],
    },
    {
        "id": "ciruelo",
        "nombre": "Ciruelo",
        "emoji": "🌳",
        "descripcion": "Ciruelo europeo de pulpa amarilla, para mermeladas y jugos.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Damson_plum_fruit.jpg/960px-Damson_plum_fruit.jpg",
                "titulo": "Damson plum fruit.jpg",
                "autor": "Jonathan Billinger",
                "licencia": "CC BY-SA 2.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Damson_plum_fruit.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Prunus_domestica_fruit.jpg/960px-Prunus_domestica_fruit.jpg",
                "titulo": "Prunus domestica fruit.jpg",
                "autor": "Franca",
                "licencia": "CC BY 2.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Prunus_domestica_fruit.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Ameixa_-_Ciruela_-_Plum_-_Prunus_-_03.jpg/960px-Ameixa_-_Ciruela_-_Plum_-_Prunus_-_03.jpg",
                "titulo": "Ameixa - Ciruela - Plum - Prunus - 03.jpg",
                "autor": "Xosema",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Ameixa_-_Ciruela_-_Plum_-_Prunus_-_03.jpg",
            },
        ],
    },
    {
        "id": "cerezo",
        "nombre": "Cerezo",
        "emoji": "🍒",
        "descripcion": "Cereza de carozo, de temporada y muy apreciada.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/8/85/Cireres_madures_del_priorat_%28Prunus_avium%29.JPG",
                "titulo": "Cireres madures del priorat (Prunus avium).JPG",
                "autor": "Netol",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Cireres_madures_del_priorat_(Prunus_avium).JPG",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Cherries_cherry_branch_fruit_red_826113.jpg/960px-Cherries_cherry_branch_fruit_red_826113.jpg",
                "titulo": "Cherries cherry branch fruit red 826113.jpg",
                "autor": "Schueler-Design",
                "licencia": "CC0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Cherries_cherry_branch_fruit_red_826113.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Sweetheart_Cherry_tree_7835.jpg/960px-Sweetheart_Cherry_tree_7835.jpg",
                "titulo": "Sweetheart Cherry tree 7835.jpg",
                "autor": "Chris Light",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Sweetheart_Cherry_tree_7835.jpg",
            },
        ],
    },
    {
        "id": "manzano",
        "nombre": "Manzano",
        "emoji": "🍏",
        "descripcion": "Manzano de mesa de tamaño compacto y buena vida poscosecha.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Malus_domestica_unriped_fruit.jpg/960px-Malus_domestica_unriped_fruit.jpg",
                "titulo": "Malus domestica unriped fruit.jpg",
                "autor": "Dinnye",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Malus_domestica_unriped_fruit.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Apple_orchards_in_Kotgarh%2821485537864%29.jpg/960px-Apple_orchards_in_Kotgarh%2821485537864%29.jpg",
                "titulo": "Apple orchards in Kotgarh(21485537864).jpg",
                "autor": "Ashish Gupta from Noida, India",
                "licencia": "CC BY 2.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Apple_orchards_in_Kotgarh(21485537864).jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Gilcrease_Orchard_Apples.jpg/960px-Gilcrease_Orchard_Apples.jpg",
                "titulo": "Gilcrease Orchard Apples.jpg",
                "autor": "Noah Wulf",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Gilcrease_Orchard_Apples.jpg",
            },
        ],
    },
    {
        "id": "duraznero",
        "nombre": "Duraznero",
        "emoji": "🍑",
        "descripcion": "Durazno de pulpa amarilla, jugoso y aromático.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Prunus_persica_-_Peach_Hungary.jpg/960px-Prunus_persica_-_Peach_Hungary.jpg",
                "titulo": "Prunus persica - Peach Hungary.jpg",
                "autor": "Takkk",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Prunus_persica_-_Peach_Hungary.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Autumn_Red_peaches.jpg/960px-Autumn_Red_peaches.jpg",
                "titulo": "Autumn Red peaches.jpg",
                "autor": "Jack Dykinga, USDA",
                "licencia": "Public domain",
                "fuente": "https://commons.wikimedia.org/wiki/File:Autumn_Red_peaches.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Peaches_at_Applecrest_Farm_Orchards_-_20108462909.jpg/960px-Peaches_at_Applecrest_Farm_Orchards_-_20108462909.jpg",
                "titulo": "Peaches at Applecrest Farm Orchards - 20108462909.jpg",
                "autor": "Allagash Brewing",
                "licencia": "CC BY 2.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Peaches_at_Applecrest_Farm_Orchards_-_20108462909.jpg",
            },
        ],
    },
    {
        "id": "membrillo",
        "nombre": "Membrillo",
        "emoji": "🍐",
        "descripcion": "Membrillo astringente, usado en mermeladas y pasteles.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Cydonia_oblonga_Quince_%E1%83%99%E1%83%9D%E1%83%9B%E1%83%A8%E1%83%98.jpg/960px-Cydonia_oblonga_Quince_%E1%83%99%E1%83%9D%E1%83%9B%E1%83%A8%E1%83%98.jpg",
                "titulo": "Cydonia oblonga Quince კომში.jpg",
                "autor": "Lazaregagnidze",
                "licencia": "CC BY-SA 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Cydonia_oblonga_Quince_%E1%83%99%E1%83%9D%E1%83%9B%E1%83%A8%E1%83%98.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Cydonia_oblonga_%27Portugal%27_1DS-II_2470.jpg/960px-Cydonia_oblonga_%27Portugal%27_1DS-II_2470.jpg",
                "titulo": "Cydonia oblonga 'Portugal' 1DS-II 2470.jpg",
                "autor": "SAplants",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Cydonia_oblonga_%27Portugal%27_1DS-II_2470.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Cydonia_oblonga_%27Portugal%27_5Dsr_2401.jpg/960px-Cydonia_oblonga_%27Portugal%27_5Dsr_2401.jpg",
                "titulo": "Cydonia oblonga 'Portugal' 5Dsr 2401.jpg",
                "autor": "SAplants",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Cydonia_oblonga_%27Portugal%27_5Dsr_2401.jpg",
            },
        ],
    },
    {
        "id": "kiwi",
        "nombre": "Kiwi",
        "emoji": "🥝",
        "descripcion": "Kiwi verde, enredadera trepadora de alta producción.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Kiwi_%28Actinidia_chinensis%29_1_Luc_Viatour.jpg/960px-Kiwi_%28Actinidia_chinensis%29_1_Luc_Viatour.jpg",
                "titulo": "Kiwi (Actinidia chinensis) 1 Luc Viatour.jpg",
                "autor": "Luc Viatour",
                "licencia": "CC BY-SA 2.5",
                "fuente": "https://commons.wikimedia.org/wiki/File:Kiwi_(Actinidia_chinensis)_1_Luc_Viatour.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Green_kiwifruit_on_vines_-_almost_ready_for_harvesting.jpg/960px-Green_kiwifruit_on_vines_-_almost_ready_for_harvesting.jpg",
                "titulo": "Green kiwifruit on vines - almost ready for harvesting.jpg",
                "autor": "Pseudopanax at English Wikipedia",
                "licencia": "Public domain",
                "fuente": "https://commons.wikimedia.org/wiki/File:Green_kiwifruit_on_vines_-_almost_ready_for_harvesting.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Kiwi_aka.jpg/960px-Kiwi_aka.jpg",
                "titulo": "Kiwi aka.jpg",
                "autor": "André Karwath aka Aka",
                "licencia": "CC BY-SA 2.5",
                "fuente": "https://commons.wikimedia.org/wiki/File:Kiwi_aka.jpg",
            },
        ],
    },
    {
        "id": "frutilla",
        "nombre": "Frutilla",
        "emoji": "🍓",
        "descripcion": "Frutilla (fresa) de huerto, rica en fibra y vitaminas.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Fragaria_vesca_2018-09-22.jpg/960px-Fragaria_vesca_2018-09-22.jpg",
                "titulo": "Fragaria vesca 2018-09-22.jpg",
                "autor": "Incnis Mrsi",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Fragaria_vesca_2018-09-22.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Erdbeerschalen_Viktualienmarkt_M%C3%BCnchen.jpg/960px-Erdbeerschalen_Viktualienmarkt_M%C3%BCnchen.jpg",
                "titulo": "Erdbeerschalen Viktualienmarkt München.jpg",
                "autor": "Thomas Wolf, www.foto-tw.de",
                "licencia": "CC BY-SA 3.0 de",
                "fuente": "https://commons.wikimedia.org/wiki/File:Erdbeerschalen_Viktualienmarkt_M%C3%BCnchen.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Garden_strawberry_%28Fragaria_%C3%97_ananassa%29_single2.jpg/960px-Garden_strawberry_%28Fragaria_%C3%97_ananassa%29_single2.jpg",
                "titulo": "Garden strawberry (Fragaria × ananassa) single2.jpg",
                "autor": "Ivar Leidus",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Garden_strawberry_(Fragaria_%C3%97_ananassa)_single2.jpg",
            },
        ],
    },
    {
        "id": "olivo",
        "nombre": "Olivo",
        "emoji": "🫒",
        "descripcion": "Olivo para aceite o consumo en mesa.",
        "fotos": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Olea_europaea_01_by-dpc.jpg/960px-Olea_europaea_01_by-dpc.jpg",
                "titulo": "Olea europaea 01 by-dpc.jpg",
                "autor": "David Perez",
                "licencia": "CC BY 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Olea_europaea_01_by-dpc.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Olea_europaea_03_by-dpc.jpg/960px-Olea_europaea_03_by-dpc.jpg",
                "titulo": "Olea europaea 03 by-dpc.jpg",
                "autor": "David Perez",
                "licencia": "CC BY 3.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Olea_europaea_03_by-dpc.jpg",
            },
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Korfu_%28GR%29%2C_Agii_Douli%2C_Olivenhain_--_2018_--_1284-8.jpg/960px-Korfu_%28GR%29%2C_Agii_Douli%2C_Olivenhain_--_2018_--_1284-8.jpg",
                "titulo": "Korfu (GR), Agii Douli, Olivenhain -- 2018 -- 1284-8.jpg",
                "autor": "Dietmar Rabich",
                "licencia": "CC BY-SA 4.0",
                "fuente": "https://commons.wikimedia.org/wiki/File:Korfu_(GR),_Agii_Douli,_Olivenhain_--_2018_--_1284-8.jpg",
            },
        ],
    },
]


def listar_especies() -> list:
    """Devuelve el catalogo completo de especies con sus fotos."""
    return CATALOGO_ESPECIES


def buscar_especie(especie_id: str) -> Optional[dict]:
    """Busca una especie por su id. Devuelve None si no existe."""
    if not especie_id:
        return None
    for especie in CATALOGO_ESPECIES:
        if especie["id"] == especie_id:
            return especie
    return None


def fotos_permitidas(especie_id: str) -> set:
    """URLs de imagenes validas para la especie indicada."""
    especie = buscar_especie(especie_id)
    if not especie:
        return set()
    return {foto["url"] for foto in especie["fotos"]}


def componer_nombre(especie_id: str, identificador: Optional[str] = None) -> str:
    """Arma el nombre visible del arbol: "Palto Hass #104"."""
    especie = buscar_especie(especie_id)
    if not especie:
        return ""
    nombre = especie["nombre"]
    extra = normalizar_identificador(identificador)
    if extra:
        nombre = f"{nombre} {extra}"
    return nombre


def normalizar_identificador(identificador: Optional[str]) -> str:
    """Limpia el identificador del arbol y le pone el # (ej: 104 -> #104)."""
    extra = (identificador or "").strip()
    if not extra:
        return ""
    if not extra.startswith("#"):
        extra = "#" + extra
    return extra


def foto_de(especie_id: str, indice: int = 0) -> str:
    """URL de una foto del catalogo. Se usa para los datos de ejemplo."""
    especie = buscar_especie(especie_id)
    if not especie or not especie["fotos"]:
        return ""
    return especie["fotos"][indice % len(especie["fotos"])]["url"]
