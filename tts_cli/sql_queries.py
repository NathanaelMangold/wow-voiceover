import pymysql
import pandas as pd
from tts_cli.env_vars import MYSQL_HOST, MYSQL_PORT, MYSQL_PASSWORD, MYSQL_USER, MYSQL_DATABASE


def make_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )


def query_dataframe_for_area(x_range, y_range, map_id):
    db = make_connection()
    sql_query = '''
WITH filtered_creatures AS (
    SELECT *
    FROM creature
    WHERE
        map = %s
        AND position_x >= %s AND position_x <= %s
        AND position_y >= %s AND position_y <= %s
),
quest_relations AS (
    SELECT 'accept' as source, qr.quest, fc.id as creature_id, fc.position_x, fc.position_y, fc.map
    FROM filtered_creatures fc
    JOIN creature_questrelation qr ON qr.id = fc.id
        UNION ALL
    SELECT 'complete' as source, qr.quest, fc.id as creature_id, fc.position_x, fc.position_y, fc.map
    FROM filtered_creatures fc
    JOIN creature_involvedrelation qr ON qr.id = fc.id
        UNION ALL
    SELECT 'progress' as source, qr.quest, fc.id as creature_id, fc.position_x, fc.position_y, fc.map
    FROM filtered_creatures fc
    JOIN creature_involvedrelation qr ON qr.id = fc.id
)
creature_data AS (
    SELECT
        filtered_creatures.id,
        ct.name,
        gm.entry AS gm_entry,
        gm.text_id AS gm_text_id,
        gm2.entry AS gm2_entry,
        gm2.text_id AS gm2_text_id,
        gm3.entry AS gm3_entry,
        gm3.text_id AS gm3_text_id,
        cdie.DisplaySexID,
        cdie.DisplayRaceID
    FROM filtered_creatures
        JOIN creature_template ct ON filtered_creatures.id = ct.entry
        JOIN db_CreatureDisplayInfo cdi ON ct.display_id1 = cdi.ID
        JOIN db_CreatureDisplayInfoExtra cdie ON cdi.ExtendedDisplayInfoID = cdie.ID
        left JOIN gossip_menu gm ON ct.gossip_menu_id = gm.entry
        left JOIN gossip_menu_option gmo ON gm.entry = gmo.menu_id
        left JOIN gossip_menu gm2 ON gmo.action_menu_id = gm2.entry
        left JOIN gossip_menu_option gmo2 ON gm2.entry = gmo2.menu_id
        left JOIN gossip_menu gm3 ON gmo2.action_menu_id = gm3.entry
),
gossip_levels AS (
    SELECT 0 AS level
    UNION ALL SELECT 1
    UNION ALL SELECT 2
),
numbers AS (
    SELECT 0 AS n
    UNION ALL SELECT 1
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
    UNION ALL SELECT 7
)
SELECT
    distinct
    qr.source,
    qr.quest,
    qt.Title as quest_title,
    CASE
        WHEN qr.source = 'accept' THEN qt.Details
        WHEN qr.source = 'progress' THEN qt.RequestItemsText
        ELSE qt.OfferRewardText
    END as "text",
    cdie.DisplayRaceID,
    cdie.DisplaySexID,
    ct.name,
    qr.creature_id as id
FROM
    quest_relations qr
JOIN quest_template qt ON qr.quest = qt.entry
JOIN creature_template ct ON qr.creature_id = ct.entry
JOIN db_CreatureDisplayInfo cdi ON ct.display_id1 = cdi.ID
JOIN db_CreatureDisplayInfoExtra cdie ON cdi.ExtendedDisplayInfoID = cdie.ID
WHERE
    (
        (qr.source = 'accept' AND qt.Details IS NOT NULL AND qt.Details != '')
        OR (qr.source = 'progress' AND qt.RequestItemsText IS NOT NULL AND qt.RequestItemsText != '')
        OR (qr.source = 'complete' AND qt.OfferRewardText IS NOT NULL AND qt.OfferRewardText != '')
    )

UNION ALL

SELECT
    distinct
    'gossip' as source,
    '' as quest,
    '' as quest_title,
    IF(creature_data.DisplaySexID = 0, bt.male_text, bt.female_text) AS text,
    creature_data.DisplayRaceID,
    creature_data.DisplaySexID,
    creature_data.name,
    creature_data.id
FROM creature_data
    CROSS JOIN gossip_levels
    CROSS JOIN numbers
    JOIN npc_text nt ON
        CASE gossip_levels.level
            WHEN 0 THEN gm_text_id
            WHEN 1 THEN gm2_text_id
            WHEN 2 THEN gm3_text_id
        END = nt.ID
    JOIN broadcast_text bt ON
        CASE numbers.n
            WHEN 0 THEN nt.BroadcastTextID0
            WHEN 1 THEN nt.BroadcastTextID1
            WHEN 2 THEN nt.BroadcastTextID2
            WHEN 3 THEN nt.BroadcastTextID3
            WHEN 4 THEN nt.BroadcastTextID4
            WHEN 5 THEN nt.BroadcastTextID5
            WHEN 6 THEN nt.BroadcastTextID6
            WHEN 7 THEN nt.BroadcastTextID7
        END = bt.entry
WHERE
    (DisplaySexID = 0 AND bt.male_text IS NOT NULL AND bt.male_text != '')
    OR (DisplaySexID = 1 AND bt.female_text IS NOT NULL AND bt.female_text != '')
;
    '''

    with db.cursor() as cursor:
        cursor.execute(
            sql_query, (map_id, x_range[0], x_range[1], y_range[0], y_range[1]))
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    db.close()
    df = pd.DataFrame(data, columns=columns)

    return df


def query_dataframe_for_all_quests_and_gossip():
    db = make_connection()
    sql_query = '''
WITH quest_relations AS (
    SELECT 'accept' as source, qr.quest, ct.entry as creature_id
    FROM creature_template ct
    JOIN creature_questrelation qr ON qr.id = ct.entry
        UNION ALL
    SELECT 'complete' as source, qr.quest, ct.entry as creature_id
    FROM creature_template ct
    JOIN creature_involvedrelation qr ON qr.id = ct.entry
        UNION ALL
    SELECT 'progress' as source, qr.quest, ct.entry as creature_id
    FROM creature_template ct
    JOIN creature_involvedrelation qr ON qr.id = ct.entry
),
creature_data AS (
    SELECT
        ct.entry as id,
        ct.name,
        gm.entry AS gm_entry,
        gm.text_id AS gm_text_id,
        gm2.entry AS gm2_entry,
        gm2.text_id AS gm2_text_id,
        gm3.entry AS gm3_entry,
        gm3.text_id AS gm3_text_id,
        cdie.DisplaySexID,
        cdie.DisplayRaceID
    FROM creature_template ct
        JOIN db_CreatureDisplayInfo cdi ON ct.display_id1 = cdi.ID
        JOIN db_CreatureDisplayInfoExtra cdie ON cdi.ExtendedDisplayInfoID = cdie.ID
        left JOIN gossip_menu gm ON ct.gossip_menu_id = gm.entry
        left JOIN gossip_menu_option gmo ON gm.entry = gmo.menu_id
        left JOIN gossip_menu gm2 ON gmo.action_menu_id = gm2.entry
        left JOIN gossip_menu_option gmo2 ON gm2.entry = gmo2.menu_id
        left JOIN gossip_menu gm3 ON gmo2.action_menu_id = gm3.entry
),
gossip_levels AS (
    SELECT 0 AS level
    UNION ALL SELECT 1
    UNION ALL SELECT 2
),
numbers AS (
    SELECT 0 AS n
    UNION ALL SELECT 1
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
    UNION ALL SELECT 7
)
SELECT
    distinct
    qr.source,
    qr.quest,
    qt.Title as quest_title,
    CASE
        WHEN qr.source = 'accept' THEN qt.Details
        WHEN qr.source = 'progress' THEN qt.RequestItemsText
        ELSE qt.OfferRewardText
    END as "text",
    cdie.DisplayRaceID,
    cdie.DisplaySexID,
    ct.name,
    qr.creature_id as id
FROM
    quest_relations qr
JOIN quest_template qt ON qr.quest = qt.entry
JOIN creature_template ct ON qr.creature_id = ct.entry
JOIN db_CreatureDisplayInfo cdi ON ct.display_id1 = cdi.ID
JOIN db_CreatureDisplayInfoExtra cdie ON cdi.ExtendedDisplayInfoID = cdie.ID
WHERE
    (
        (qr.source = 'accept' AND qt.Details IS NOT NULL AND qt.Details != '')
        OR (qr.source = 'progress' AND qt.RequestItemsText IS NOT NULL AND qt.RequestItemsText != '')
        OR (qr.source = 'complete' AND qt.OfferRewardText IS NOT NULL AND qt.OfferRewardText != '')
    )
UNION ALL
SELECT
    distinct
    'gossip' as source,
    '' as quest,
    '' as quest_title,
    IF(creature_data.DisplaySexID = 0, bt.male_text, bt.female_text) AS text,
    creature_data.DisplayRaceID,
    creature_data.DisplaySexID,
    creature_data.name,
    creature_data.id
FROM creature_data
    CROSS JOIN gossip_levels
    CROSS JOIN numbers
    JOIN npc_text nt ON
        CASE gossip_levels.level
            WHEN 0 THEN gm_text_id
            WHEN 1 THEN gm2_text_id
            WHEN 2 THEN gm3_text_id
        END = nt.ID
    JOIN broadcast_text bt ON
        CASE numbers.n
            WHEN 0 THEN nt.BroadcastTextID0
            WHEN 1 THEN nt.BroadcastTextID1
            WHEN 2 THEN nt.BroadcastTextID2
            WHEN 3 THEN nt.BroadcastTextID3
            WHEN 4 THEN nt.BroadcastTextID4
            WHEN 5 THEN nt.BroadcastTextID5
            WHEN 6 THEN nt.BroadcastTextID6
            WHEN 7 THEN nt.BroadcastTextID7
        END = bt.entry
WHERE
    (DisplaySexID = 0 AND bt.male_text IS NOT NULL AND bt.male_text != '')
    OR (DisplaySexID = 1 AND bt.female_text IS NOT NULL AND bt.female_text != '')
;
    '''

    with db.cursor() as cursor:
        cursor.execute(sql_query)
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    db.close()
    df = pd.DataFrame(data, columns=columns)

    return df
