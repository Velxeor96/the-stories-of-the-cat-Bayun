# sources_config.py
# Конфиг: какие страницы парсить, куда сохранять, адаптировать ли через GigaChat.
#
# Поля:
#   api           — "mediawiki" или "html".
#   source        — чистильщик: "lexicanum", "fandom", "generic".
#   urls, fallback_urls, wayback_urls, search_queries — источники.
#   adapt         — true (по умолчанию): адаптировать через GigaChat.
#                   false: сохранять сырой текст (для глоссариев, терминологий).
#   folder, name  — куда сохранять.
#   description   — описание для --list.

SOURCES = {

    # ============================================================
    # ЭЛЬДАРЫ
    # ============================================================
    "eldar": {
        "spacecraft": {
            "api": "mediawiki", "source": "lexicanum", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Eldar spacecraft", "Aeldari fleet", "Eldar ship classes",
            ],
            "folder": "eldar", "name": "spacecraft",
            "description": "Космический флот Аэльдари (адаптируется под RT).",
        },
        "aspect_warriors_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Eldar Aspect Warriors", "Howling Banshees",
                "Striking Scorpions", "Dark Reapers",
            ],
            "folder": "eldar", "name": "aspect_warriors_extra",
            "description": "Аспектные Воины с игровыми профилями.",
        },
        "harlequins": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Harlequin", "Cegorach", "Laughing God",
                "Harlequin Troupe", "Solitaire Harlequin",
            ],
            "folder": "eldar", "name": "harlequins",
            "description": "Арлекины и Смеющийся Бог Цегорах.",
        },
    },

    # ============================================================
    # ИМПЕРИУМ
    # ============================================================
    "imperium": {
        "spacecraft": {
            "api": "mediawiki", "source": "lexicanum", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Imperial Navy", "Imperial spacecraft",
            ],
            "folder": "imperium", "name": "spacecraft",
            "description": "Космический флот Империума.",
        },
        "space_marines_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Space Marine", "Adeptus Astartes", "Space Marine Chapters",
            ],
            "folder": "imperium", "name": "space_marines_extra",
            "description": "Космодесант с игровыми профилями.",
        },
        "imperial_guard_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [],
            "fallback_urls": [],
            "wayback_urls": [],
            "search_queries": [
                "Imperial Guard", "Astra Militarum", "Cadian Shock Troops",
            ],
            "folder": "imperium", "name": "imperial_guard_extra",
            "description": "Имперская Гвардия.",
        },
        "inquisition": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [
                "https://warhammer40k.fandom.com/wiki/Inquisition",
            ],
            "fallback_urls": [
                "https://warhammer40k.fandom.com/wiki/Inquisitor",
                "https://warhammer40k.fandom.com/wiki/Ordo_Malleus",
                "https://warhammer40k.fandom.com/wiki/Ordo_Hereticus",
                "https://warhammer40k.fandom.com/wiki/Ordo_Xenos",
            ],
            "wayback_urls": [],
            "search_queries": [
                "Inquisition", "Inquisitor",
            ],
            "folder": "imperium", "name": "inquisition",
            "description": "Инквизиция: ордоса, пути (пуритане/радикалы), методы.",
        },
    },

    # ============================================================
    # ХАОС
    # ============================================================
    "chaos": {
        "spacecraft": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": ["Chaos Fleet", "Chaos spacecraft"],
            "folder": "chaos", "name": "spacecraft",
            "description": "Космический флот Хаоса.",
        },
        "daemons_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Chaos Daemons", "Bloodletter", "Plaguebearer",
                "Daemonette", "Horror of Tzeentch",
            ],
            "folder": "chaos", "name": "daemons_extra",
            "description": "Демоны Хаоса с игровыми профилями.",
        },
        "drukhari": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [
                "https://warhammer40k.fandom.com/wiki/Drukhari",
            ],
            "fallback_urls": [
                "https://warhammer40k.fandom.com/wiki/Dark_Eldar",
                "https://warhammer40k.fandom.com/wiki/Commorragh",
            ],
            "wayback_urls": [],
            "search_queries": [
                "Drukhari", "Dark Eldar",
            ],
            "folder": "chaos", "name": "drukhari",
            "description": "Друкхари: кабалы, культы вий, ковены гемункулов.",
        },
    },

    # ============================================================
    # ОРКИ
    # ============================================================
    "orks": {
        "spacecraft": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Ork spacecraft", "Ork ship classes", "Ork fleet",
            ],
            "folder": "orks", "name": "spacecraft",
            "description": "Космический флот орков.",
        },
        "warbands_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Ork Warboss", "Ork Boyz", "Ork Nob", "Waaagh",
            ],
            "folder": "orks", "name": "warbands_extra",
            "description": "Орочьи отряды с игровыми профилями.",
        },
    },

    # ============================================================
    # ТАУ
    # ============================================================
    "tau": {
        "spacecraft": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": ["Tau fleet", "Tau Navy", "Tau spacecraft"],
            "folder": "tau", "name": "spacecraft",
            "description": "Космический флот Тау.",
        },
        "battlesuits_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Tau Battlesuit", "Crisis Battlesuit", "Fire Warrior",
            ],
            "folder": "tau", "name": "battlesuits_extra",
            "description": "Тау-воины с игровыми профилями.",
        },
    },

    # ============================================================
    # НЕКРОНЫ
    # ============================================================
    "necrons": {
        "spacecraft": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": ["Necron fleet", "Necron spacecraft"],
            "folder": "necrons", "name": "spacecraft",
            "description": "Флот некронов.",
        },
        "units_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Necron Warrior", "Necron Immortal", "Necron Lord",
            ],
            "folder": "necrons", "name": "units_extra",
            "description": "Некронские юниты с игровыми профилями.",
        },
    },

    # ============================================================
    # ТИРАНИДЫ
    # ============================================================
    "tyranids": {
        "spacecraft": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": ["Tyranid bio-ship", "Tyranid fleet"],
            "folder": "tyranids", "name": "spacecraft",
            "description": "Биокорабли тиранидов.",
        },
        "biomorphs_extra": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Termagant", "Hormagaunt", "Carnifex", "Hive Tyrant",
            ],
            "folder": "tyranids", "name": "biomorphs_extra",
            "description": "Биоморфы тиранидов с профилями.",
        },
    },

    # ============================================================
    # ОБЩЕЕ
    # ============================================================
    "general": {
        "chaos_gods": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Chaos Gods", "Khorne", "Tzeentch", "Nurgle", "Slaanesh",
            ],
            "folder": "general", "name": "chaos_gods",
            "description": "Боги Хаоса.",
        },
        "imperial_creed": {
            "api": "mediawiki", "source": "fandom", "adapt": True,
            "urls": [], "fallback_urls": [], "wayback_urls": [],
            "search_queries": [
                "Imperial Creed", "Adeptus Ministorum", "Ecclesiarchy",
            ],
            "folder": "general", "name": "imperial_creed",
            "description": "Имперское Кредо.",
        },
    },
}