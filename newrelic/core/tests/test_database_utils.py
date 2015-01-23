from __future__ import print_function

import unittest

from newrelic.core.database_utils import (SQLStatement,
    _query_result_dicts_to_tuples)

GENERAL_PARSE_TESTS = [
    (
        # Empty.
        ('', ''),
        ""
    ),
    (
        # Empty (whitespace).
        ('', ''),
        " "
    ),
    (
        # Invalid.
        ('', 'select'),
        """select"""
    ),
]

COMMENT_PARSE_TESTS = [
  (
    # Multi-line comment (Java Agent TestCase)
    ('dude1', 'select'),
    """/* this comment
            is crazy.
            yo
        */ select * from dude1"""
  ),
  (
    # Comment in middle (dotNet Agent TestCase)
    ('dude2', 'select'),
    """select *
    /* ignore the comment */
    from dude2
    """
  ),
]

SELECT_PARSE_TESTS = [
  (
    # Select.
    ('student_details', 'select'),
    """SELECT first_name FROM student_details"""
  ),
  (
    # Select using alias.
    ('student_details', 'select'),
    """SELECT first_name Name FROM student_details"""
  ),
  (
    # Select using alias.
    ('student_details', 'select'),
    """SELECT first_name AS Name FROM student_details"""
  ),
  (
    # Select using table alias.
    ('student_details', 'select'),
    """SELECT s.first_name FROM student_details s"""
  ),
  (
    # Select using table alias.
    ('student_details', 'select'),
    """SELECT s.first_name FROM student_details AS s"""
  ),
  (
    # Select with condition.
    ('student_details', 'select'),
    """SELECT first_name, last_name FROM student_details WHERE id = 100"""
  ),
  (
    # Select with condition and alias.
    ('employee', 'select'),
    """SELECT name, salary, salary*1.2 AS new_salary FROM employee
    WHERE salary*1.2 > 30000"""
  ),
  (
    # Select with sub query.
    ('student_details', 'select'),
    """SELECT id, first_name FROM student_details WHERE first_name
    IN (SELECT first_name FROM student_details WHERE subject= 'Science')"""
  ),
  (
    # "Select with correlated sub query using table alias.
    ('product', 'select'),
    """SELECT p.product_name FROM product p WHERE p.product_id = (SELECT
    o.product_id FROM order_items o WHERE o.product_id = p.product_id)"""
  ),
  (
    # Select with correlated sub query using table alias.
    ('employee', 'select'),
    """SELECT employee_number, name FROM employee AS e1 WHERE salary >
    (SELECT avg(salary) FROM employee WHERE department = e1.department)"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('app_devicesoftware', 'select'),
    """SELECT * FROM ( SELECT s.*, ds.version AS version2, ds.installed
    FROM app_devicesoftware ds, app_software s, app_vendor v WHERE s.id =
    ds.software_id AND s.manufacturer_id = v.id AND s.manufacturer_id <> %s
    AND s.approved = true AND v.approved = True AND installed IS NOT NULL
    AND ds.version IS NOT NULL ORDER BY name ASC, ds.version DESC,
    installed ASC ) AS temp GROUP BY id ORDER BY installed DESC LIMIT ?"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('app_component', 'select'),
    """SELECT COUNT(t.manufacturer_id) AS total, v.* FROM ( SELECT
    c.manufacturer_id FROM app_component c WHERE manufacturer_id <> %s GROUP BY
    c.model, c.manufacturer_id ) AS t, app_vendor v WHERE v.id =
    t.manufacturer_id AND v.approved = true GROUP BY t.manufacturer_id ORDER BY
    COUNT(t.manufacturer_id) DESC LIMIT ?"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('photos', 'select'),
    """SELECT count(?) AS count_1 FROM (SELECT DISTINCT photos.id AS photos_id
    FROM photos, item_map WHERE item_map.to_id IN (%s) AND item_map.to_type =
    %s AND item_map.from_id = photos.id AND item_map.from_type = %s AND
    item_map.deleted = %s) AS anon_1"""
  ),
  (
    # Select with sub query.
    ('entity_entity', 'select'),
    """SELECT COUNT(*) FROM (SELECT "entity_entity"."id" AS "id",
    "entity_site"."id" AS Col1, "entity_site"."updated_at",
    "entity_site"."created_at", "entity_site"."domain",
    "entity_site"."popularity_multiplier", "entity_site"."clicks",
    "entity_site"."monetized_clicks", "entity_site"."epc",
    "entity_site"."commission", "entity_site"."category_id",
    "entity_site"."subdomain", "entity_site"."blocked",
    "entity_site"."in_shop_list", "entity_site"."related_user_id",
    "entity_site"."description", "entity_site"."shop_name",
    "entity_site"."order", "entity_site"."featured",
    "entity_site"."shop_data_complete", "entity_site"."shop_url" FROM
    "entity_entity" LEFT OUTER JOIN "entity_site" ON
    ("entity_entity"."site_id" = "entity_site"."id")
    WHERE (NOT (("entity_site"."category_id" IN (%s, %s) AND NOT
    ("entity_site"."id" IS NULL))) AND "entity_entity"."id" <= %s
    ) LIMIT ?) subquery"""
  ),
  (
    # Select from union of sub queries.
    ('t1', 'select'),
    """select * from (select * from t1 union select * from t2)"""
  ),
  (
    # Select from union of sub queries.
    ('t1', 'select'),
    """select * from ((select * from t1) union (select * from t2))"""
  ),
  (
    # Select from union all of sub queries.
    ('t1', 'select'),
    """select * from (select * from t1 union all select * from t2)"""
  ),
  (
    # Select from union all of sub queries.
    ('t1', 'select'),
    """select * from ((select * from t1) union all (select * from t2))"""
  ),
  (
    # Select from union all of sub queries with limit.
    ('t1', 'select'),
    """(select * from (select * from t1 union all select * from t2)) limit 1"""
  ),
  (
    # Additional nested brackets.
    ('t1', 'select'),
    """((select * from (select * from t1))) limit 1"""
  ),
  (
    # Additional nested brackets with a space.
    ('t1', 'select'),
    """( ( select * from (select * from t1))) limit 1"""
  ),
  (
    # Additional nested brackets.
    ('t1', 'select'),
    """(select * from ((select * from t1))) limit 1"""
  ),
  (
    # Select with sub query. (Java agent test case)
    ('dude', 'select'),
    """select * from (select * from dude)""",
  ),
  (
    # Select with sub query. (Java agent test case)
    ('customers', 'select'),
    """SELECT t.* FROM (SELECT ROW_NUMBER() OVER(ORDER BY customers.ad_channel
    DESC) AS _row_num, * FROM [customers] WHERE (? = ?)) AS t WHERE t._row_num
    BETWEEN ? AND ?""",
  ),
  (
    # Select with sub query. (Java agent test case)
    ('prod_lock', 'select'),
    """select * from (select s.rush, NVL(NVL(o.postor, o.finalizer),
    o.assignedPM)assignedPM, o.orderid, (case when (l.expiration IS NULL or
    l.expiration<SYSDATE ) then ? else ? end) isLocked, o.design,
    to_char(s.dtb_release, ?) dtb_release, to_char(s.dt_release, ?) dt_release,
    o.printer, o.totalunits, o.totalprice from prod_lock l, (select orderid
    from wm_order where dt_placed between to_date(?, ?) and SYSDATE+? and
    tracking_no is not null) a, (select x.orderid, x.dtb_release, x.dt_release,
    x.rush from prod_sched x where x.dt_extra? IS NULL and (NOT EXISTS (select
    pp.orderid from prod_printcalc pp where pp.orderid=x.orderid)) and
    x.dt_finalize IS NOT NULL and x.dt_finalize between to_date(?, ?) and
    SYSDATE and x.dt_process is not null and x.dt_proof is not null )s,
    (select * from prod_overview where printer NOT IN (?, ?, ? ))o, (select
    orderid from prod_print where method !=?)p, (select distinct orderid
    from prod_blank where source !=?)bl where s.orderid=o.orderid and
    o.orderid=a.orderid and a.orderid=l.orderid and a.orderid=p.orderid and
    a.orderid=bl.orderid order by s.dtb_release, decode(s.rush, ?, ?, ?, ?,
    decode(s.rush, ?, ?, ?)) , a.orderid ) where rownum <= ?""",
  ),
  (
    # Select with sub query. (Java agent test case)
    ('plan_features_view', 'select'),
    """select ent.PLAN_PLAN_PRIORITY, ent.TYPE_ID, ent.TYPE,
    ent.PRIMARY_RELEASE, ent.IS_PARENT, ent.NAME, ent.ID, ent.OWNER_NAME,
    ent.OWNER_STATUS, ent.SERIAL_NUMBER, ent.ADDITIONAL_RELEASE,
    ent.RELEASE_NAME, PLAN_REF_ENTITY,"PLAN",INVEST_EST_AGGREGATED,
    PLAN_NODE_ID,seq.NODE_ID from (select ent1.*,"PLAN" as PLAN_NODE_ID from
    PLAN_FEATURES_VIEW ent1) ent,COMN_HIERARCHY_SEQ seq where ent."PLAN"=?
    and (1=1 and ((ent.ACCESS_MODE in (-1,0,1,2)) or ent.OWNER=? or ent.OWNER
    in (select gu.GROUP_ID as OWNER from USR_GROUP_USER gu where gu.USER_ID=?)
    or (ent.ACCESS_MODE=6 and (ent.ID in (select pem.ENTITY_ID as ID from
    V_PRINCIPAL_ENTITY_MEMBERSHIP pem where pem.MEMBER_ID=?) or ent.ID in
    (select ENTITY_ID as ID from COMN_ENTITY_STAKEHOLDER_REL where USER_ID=?)))
    or ( ent.ACCESS_MODE=6 and exists( select 0 from (select OWNER,ID as
    ENTITY_ID from WKFL_ENT_ACT_PROT_U_VIEW) act where act.ENTITY_ID=ent.ID and
    (act.OWNER=?)))) and (ent.TYPE_ID=0 or (ent.TYPE_ID>0 and exists(select 0
    from (select ID as REL_GROUP_ID,ENTITY_TYPE_ID as REL_ENTITY_TYPE_ID from
    REL_GROUP_SUB_TYPE_VIEW) rel, USR_GROUP_USER gu where
    rel.REL_ENTITY_TYPE_ID=ent.TYPE_ID and rel.REL_GROUP_ID=gu.GROUP_ID and
    gu.USER_ID=?)))) and seq.NODE_ID=ent.ID order by PRIMARY_RELEASE
    desc,seq.HIERARCH_SEQ,seq.LVL,seq.SN""",
  ),
  (
    # Select with sub query. (Java agent test case)
    ('product', 'select'),
    """SELECT
    Product.Id,Product.Cost,Product.Name,Product.Summary,Product.Availability
    FROM `Product` WHERE Id IN (SELECT ProductId FROM ProductTaxonomy WHERE
    TaxId=220) AND Active = 1 AND Id NOT IN (Select AssocId FROM
    ProductPairing) ORDER BY Name LIMIT 15 OFFSET 120""",
  ),
  (
    # Select with sub query. (Java agent test case)
    ('std_data.city_deals', 'select'),
    """select citydeal1_.cd_id as cd1_1_1_, merchant1_.dm_id as dm1_1_1_,
    citydeal1_.cd_appdomain_id as cd1_1_1_, citydeal1_.cd_canonical_tag as
    cd1_1_1_, citydeal1_.cd_ptc_city_id as cd1_1_1_,
    citydeal1_.cd_coupon_how_it_works as cd1_1_1_,
    citydeal1_.cd_deal_title_coupon as cd1_1_1_,
    citydeal1_.cd_deal_email_type as cd1_1_1_, citydeal1_.cd_dlg_id as
    cd1_1_1_, citydeal1_.cd_deal_type_id as cd1_1_1_,
    citydeal1_.cd_deal_end_time as cd1_1_1_, citydeal1_.cd_short_highlights
    as cd1_1_1_, citydeal1_.cd_image_big as cd1_1_1_,
    citydeal1_.cd_image_newsletter as cd1_1_1_,
    citydeal1_.cd_sidedeal_image as cd1_1_1_, citydeal1_.cd_image_small as
    cd1_1_1_, citydeal1_.cd_last_modified as cd1_1_1_,
    citydeal1_.cd_long_description as cd1_1_1_,
    citydeal1_.cd_customer_index_max as cd1_1_1_,
    citydeal1_.cd_participant_maximum as cd1_1_1_,
    citydeal1_.cd_merchant_id as cd1_1_1_, citydeal1_.cd_meta_description
    as cd1_1_1_, citydeal1_.cd_meta_keywords as cd1_1_1_,
    citydeal1_.cd_meta_title as cd1_1_1_, citydeal1_.cd_participant_minimum
    as cd1_1_1_, citydeal1_.cd_mobile_description as cd1_1_1_,
    citydeal1_.cd_mulligan_enabled as cd1_1_1_,
    citydeal1_.cd_mulligan_parent as cd1_1_1_,
    citydeal1_.cd_multideal_parent as cd1_1_1_,
    citydeal1_.cd_multideal_type as cd1_1_1_,
    citydeal1_.cd_newsletter_side_deal_title as cd1_1_1_,
    citydeal1_.cd_newsletter_subject as cd1_1_1_,
    citydeal1_.cd_newsletter_textblock as cd1_1_1_,
    citydeal1_.cd_newsletter_title as cd1_1_1_,
    citydeal1_.cd_original_price_gross as cd1_1_1_,
    citydeal1_.cd_special_price_gross as cd1_1_1_,
    citydeal1_.cd_deal_priority as cd1_1_1_, citydeal1_.cd_salesforce_id as
    cd1_1_1_, citydeal1_.cd_deal_start_time as cd1_1_1_,
    citydeal1_.cd_scheduled_for_newsletter as cd1_1_1_,
    citydeal1_.cd_voucher_send_by_sms as cd1_1_1_,
    citydeal1_.cd_short_description as cd1_1_1_, citydeal1_.cd_sms_prefix
    as cd1_1_1_, citydeal1_.cd_participant_current as cd1_1_1_,
    citydeal1_.cd_deal_status as cd1_1_1_, citydeal1_.cd_special_price_tax
    as cd1_1_1_, citydeal1_.cd_title as cd1_1_1_,
    citydeal1_.cd_title_for_url_permalink as cd1_1_1_,
    citydeal1_.cd_coupon_valid_from as cd1_1_1_,
    citydeal1_.cd_coupon_valid_until as cd1_1_1_,
    citydeal1_.cd_voucher_delivery_event as cd1_1_1_,
    citydeal1_.cd_mvc_pool_id as cd1_1_1_, merchant1_.dm_appdomain_id as
    dm1_1_1_, merchant1_.dm_merchant_city as dm1_1_1_, merchant1_.dm_email
    as dm1_1_1_, merchant1_.dm_fax_number as dm1_1_1_,
    merchant1_.dm_merchant_googlemaps_ref as dm1_1_1_,
    merchant1_.dm_merchant_homepage as dm1_1_1_,
    merchant1_.dm_last_modified as dm1_1_1_, merchant1_.dm_merchant_logo as
    dm1_1_1_, merchant1_.dm_mulligan_enabled as dm1_1_1_,
    merchant1_.dm_merchant_company_name as dm1_1_1_,
    merchant1_.dm_merchant_opening_hours as dm1_1_1_,
    merchant1_.dm_password as dm1_1_1_, merchant1_.dm_merchant_phone as
    dm1_1_1_, merchant1_.dm_status as dm1_1_1_,
    merchant1_.dm_merchant_street as dm1_1_1_,
    merchant1_.dm_merchant_street_number as dm1_1_1_,
    merchant1_.dm_merchant_welcome_message as dm1_1_1_,
    merchant1_.dm_merchant_zipcode as dm1_1_1_ from `std_data.city_deals`
    citydeal1_ inner join std_data.deal_merchant merchant1_ on
    citydeal1_.cd_merchant_id=merchant1_.dm_id where citydeal1_.cd_id=1
    limit 1""",
  ),
  (
    # Select. (dotNet agent test case)
    ('dude', 'select'),
    """select * from [dude]"""
  ),
  (
    # Select with sub query. (PHP agent test case)
    ('hp_comments', 'select'),
    """(SELECT SQL_CALC_FOUND_ROWS c., e.entry_id, e.entry_title,
    `ee`.`entry_extra_image` AS `entry_image` FROM `hp_comments` c,
    `mt_entry` e , mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) UNION ALL
    (SELECT c., e.entry_id, e.entry_title, `ee`.`entry_extra_image` AS
    `entry_image` FROM `HPCommentsArchive?` c, `mt_entry` e ,
    mt_entry_extra ee WHERE e.`entry_id` = c.`entry_id` AND
    `ee`.`entry_extra_id` = `e`.`entry_id` AND `published` = ? AND
    `removed` = ? AND `user_id` = ? ) UNION ALL (SELECT c., e.entry_id,
    e.entry_title, `ee`.`entry_extra_image` AS `entry_image` FROM
    `HPCommentsArchive?` c, `mt_entry` e , mt_entry_extra ee WHERE
    e.`entry_id` = c.`entry_id` AND `ee`.`entry_extra_id` = `e`.`entry_id`
    AND `published` = ? AND `removed` = ? AND `user_id` = ? ) ORDER BY
    `created_on` DESC LIMIT ?, ? / app?.nyc.huffpo.net, slave-db /""",
  ),
  (
    # Select with sub query.
    ('pstat_tenant', 'select'),
    """SELECT MAX(c) FROM (SELECT `pstat_tenant`.`id` AS `id`,
    `pstat_tenant`.`name` AS `name`, `pstat_tenant`.`subdomain` AS `subdomain`,
    `pstat_tenant`.`customer_id` AS `customer_id`, `pstat_tenant`.`login_token`
    AS `login_token`, `pstat_tenant`.`old_login_token` AS `old_login_token`,
    `pstat_tenant`.`token_update_date` AS `token_update_date`,
    `pstat_tenant`.`created` AS `created`, `pstat_tenant`.`modified` AS
    `modified`, COUNT(`document`.`id`) AS `c` FROM `pstat_tenant` LEFT OUTER
    JOIN `bloc_bloc_tenants` ON (`pstat_tenant`.`id` =
    `bloc_bloc_tenants`.`tenant_id`) LEFT OUTER
    JOIN `bloc_bloc` ON (`bloc_bloc_tenants`.`bloc_id` = `bloc_bloc`.`id`) LEFT
    OUTER JOIN `document` ON (`bloc_bloc`.`id` = `document`.`bloc_id`) GROUP BY
    `pstat_tenant`.`id` ORDER BY NULL) subquery"""
  ),
  (
    # Select with special char in table name
    ('v$session', 'select'),
    """SELECT count(*) theCount FROM v$session WHERE client_info = ?"""
  ),
  (
    # Select with special char in table name
    ('krusher', 'select'),
    """select krusher?_.id as id?_?_, location?_.id as id?_?_, followers?_.id
    as id?_?_, followees?_.id as id?_?_, krusher?_.ban_info as ban?_?_?_,
    krusher?_.birth_date as birth?_?_?_, krusher?_.campaign as campaign?_?_,
    krusher?_.click_id as click?_?_?_, krusher?_.email as email?_?_,
    krusher?_.facebook_oauth_token as facebook?_?_?_,
    krusher?_.facebook_user_id as facebook?_?_?_, krusher?_.gender as
    gender?_?_, krusher?_.likes as likes?_?_, krusher?_.posts as posts?_?_,
    krusher?_.crew as crew?_?_, krusher?_.week_likes as week?_?_?_,
    krusher?_.week_posts as week?_?_?_, krusher?_.weekly_stats_date as
    weekly?_?_?_, krusher?_.last_ip as last?_?_?_, krusher?_.last_login_date as
    last?_?_?_, krusher?_.location as location?_?_, krusher?_.nickname as
    nickname?_?_, krusher?_.partner as partner?_?_, krusher?_.referrer as
    referrer?_?_, krusher?_.sign_up_date as sign?_?_?_, location?_.city as
    city?_?_, location?_.country as country?_?_,
    location?_.facebook_location_id as facebook?_?_?_, location?_.state as
    state?_?_, location?_.zip as zip?_?_, followers?_.following as
    following?_?_, followers?_.krusher_from as krusher?_?_?_,
    followers?_.krusher_to as krusher?_?_?_, followers?_.social_network as
    social?_?_?_, followers?_.krusher_to as krusher?_?__, followers?_.id as
    id?__, followees?_.following as following?_?_, followees?_.krusher_from as
    krusher?_?_?_, followees?_.krusher_to as krusher?_?_?_,
    followees?_.social_network as social?_?_?_, followees?_.krusher_from as
    krusher?_?__, followees?_.id as id?__ from krusher krusher?_ left outer
    join location location?_ on krusher?_.location=location?_.id left outer
    join friend followers?_ on krusher?_.id=followers?_.krusher_to left outer
    join friend followees?_ on krusher?_.id=followees?_.krusher_from where
    krusher?_.facebook_oauth_token=?"""
  ),
  (
    # Select. (Java Agent TestCase)
    ('prod_peml', 'select'),
    """select pemlid, message, to_char(dt_modified, 'MM/DD\"<br>\"HH:MIAM'),
    to_char(dt_sent, 'MM/DD\"<br>\"HH:MIAM'), to_char(dt_open,
    'MM/DD\"<br>\"HH:MIAM'), to_char(dt_yes, 'MM/DD\"<br>\"HH:MIAM'),
    to_char(dt_no, 'MM/DD\"<br>\"HH:MIAM'), to_char(dt_cancel,
    'MM/DD\"<br>\"HH:MIAM'), replace(peml_notes, ' ', '<BR>'),
    replace(cust_notes, ' ', '<BR>'), rep, decode(peml_type, '1', 'req',
    'opt'), NVL(sign(sysdate-(900/86400)-NVL(dt_yes, dt_no)), '0') from
    prod_peml where orderid='776371' order by pemlid"""
  ),
  (
    # Select with double-quoted table name (Java Agent TestCase)
    ('metrics2', 'select'),
    """
    SELECT * from "metrics2"
    """
  ),
  (
    # Select with single-quoted table name (Java Agent TestCase)
    ('metrics1', 'select'),
    """SELECT * from 'metrics1'"""
  ),
  (
    # Select large value set.
    ('t1', 'select'),
    """SELECT * from 't1' WHERE c1 in (%s""" + (50000*""",%s""") + """)""",
  ),
  (
    # Select with table name in parenthesis (php agent TestCase)
    # FAIL
    ('foobar', 'select'),
    """SELECT * FROM (foobar)"""
  ),
  (
    # Select with no from clause.
    # FAIL
    ('', 'select'),
    """select now() as time"""
  ),
  (
    # Select with schema.
    ('schema.table', 'select'),
    '''SELECT * from schema.table'''
  ),
  (
    # Select with quoted schema.
    ('schema.table', 'select'),
    '''SELECT * from "schema"."table"'''
  ),
  (
    # Select with quoted schema.
    ('schema.table', 'select'),
    """SELECT * from 'schema'.'table'"""
  ),
  (
    # Select with quoted schema.
    ('schema.table', 'select'),
    '''SELECT * from `schema`.`table`'''
  ),
]

DELETE_PARSE_TESTS = [
  (
    # Delete.
    ('employee', 'delete'),
    """DELETE FROM employee"""
  ),
  (
    # Delete with condition.
    ('employee', 'delete'),
    """DELETE FROM employee WHERE id = 100"""
  ),
  (
    # Delete with sub query.
    ('t1', 'delete'),
    """DELETE FROM t1 WHERE s11 > ANY (SELECT COUNT(*) /* no hint */ FROM
    t2 WHERE NOT EXISTS (SELECT * FROM t3 WHERE ROW(5*t2.s1,77)= (SELECT
    50,11*s1 FROM t4 UNION SELECT 50,77 FROM (SELECT * FROM t5) AS t5)))"""
  ),
]

INSERT_PARSE_TESTS = [
  (
    # Insert.
    ('employee', 'insert'),
    """INSERT INTO employee
    VALUES (105, 'Srinath', 'Aeronautics', 27, 33000)"""
  ),
  (
    # Insert.
    ('employee', 'insert'),
    """INSERT INTO employee (id, name, dept, age, salary location)
    VALUES (105, 'Srinath', 'Aeronautics', 27, 33000)"""
  ),
  (
    # Insert from select.
    ('employee', 'insert'),
    """INSERT INTO employee SELECT * FROM temp_employee"""
  ),
  (
    # Insert from select.
    ('employee', 'insert'),
    """INSERT INTO employee (id, name, dept, age, salary location) SELECT
    emp_id, emp_name, dept, age, salary, location FROM temp_employee"""
  ),
  (
    # Insert with no space between table name and ()
    ('test', 'insert'),
    """insert   into test(id, name) values(6, 'Bubba')"""
  )
]

UPDATE_PARSE_TESTS = [
  (
    # Update.
    ('employee', 'update'),
    """UPDATE employee SET location ='Mysore' WHERE id = 101"""
  ),
  (
    # Update.
    ('employee', 'update'),
    """UPDATE employee SET salary = salary + (salary * 0.2)"""
  ),
  (
    # Update.
    ('users_user', 'update'),
    """UPDATE users_user SET birthday=%(birthday)s,
    change_date=TIMEZONE(%(TIMEZONE_1)s, now()) WHERE users_user.id =
    %(users_user_id)s"""
  ),
]

CREATE_PARSE_TESTS = [
  (
    # Create.
    ('temp_employee', 'create'),
    """CREATE TABLE temp_employee SELECT * FROM employee"""
  ),
  (
    # Create.
    ('employee', 'create'),
    """CREATE TABLE employee ( id number(5), name char(20), dept char(10),
    age number(2), salary number(10), location char(10) )"""
  ),
  (
    # Create.
    # FAIL
    ('my table', 'create'),
    """CREATE TABLE "my table" ("my column" INT)"""
  ),
]

CALL_PARSE_TESTS = [
  (
    # Call.
    ('foo', 'call'),
    """CALL FOO(1, 2) """
  ),
  (
    # Call.
    ('foo', 'call'),
    """CALL FOO 1 2 """
  ),
]

EXEC_PARSE_TESTS = [
  (
    # Call.
    ('tsip_api_rates_lookup_intl', 'exec'),
    """EXEC TSIP_API_RATES_LOOKUP_INTL"""
  ),
  (
    # Call.
    ('dagetaccount', 'execute'),
    """EXECUTE DAGetAccount @AccountID=?,@IncludeLotLinks=?"""
  ),
]

SHOW_PARSE_TESTS = [
  (
    # Show.
    ('profiles', 'show'),
    """SHOW PROFILES"""
  ),
  (
    # Show.
    ('columns from mytable from mydb', 'show'),
    """SHOW COLUMNS FROM mytable FROM mydb"""
  ),
  (
    # Show.
    ('columns from mydb.mytable', 'show'),
    """SHOW COLUMNS FROM mydb.mytable"""
  ),
  (
    # Show long name
    ('wow_this_is_a_really_long_name_isnt_it_cmon_man_it_s_crazy_no_way_bruh',
        'show'),
    """show
    wow_this_is_a_really_long_name_isnt_it_cmon_man_it_s_crazy_no_way_bruh"""),

]

SET_PARSE_TESTS = [
  (
    # Set.
    ('language', 'set'),
    """SET LANGUAGE Australian"""
  ),
  (
    # Set.
    ('auto', 'set'),
    """SET AUTO COMMIT ON"""
  ),
  (
    # Set.
    ('transaction', 'set'),
    """SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"""
  ),
  (
    # Set with equals sign
    ('character_set_results', 'set'),
    """SET character_set_results=NULL"""
  ),
  (
    # Compound statment
    # FAIL
    ('foo', 'set'),
    """set FOO=17; set BAR=18"""
  ),
]

ALTER_PARSE_TESTS = [
  # alter
  (
      ('session', 'alter'),
      """ALTER SESSION SET ISOLATION_LEVEL = READ COMMITTED"""
  ),
]

SQL_NORMALIZE_TESTS = [
  """SELECT c1 FROM t1 WHERE c1 IN (1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN (1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1,2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1,2,3)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1, 2, 3, 4 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1,2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1 ,2)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1 ,2)""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1')""",
  """SELECT c1 FROM t1 WHERE c1 IN ( '1')""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1' )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( '1' )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n'1')""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1'\n )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n'1'\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1','2')""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1','2','3')""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1', '2', '3', '4' )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( '1','2')""",
  """SELECT c1 FROM t1 WHERE c1 IN ('1' ,'2')""",
  """SELECT c1 FROM t1 WHERE c1 IN ( '1' ,'2')""",
  """SELECT c1 FROM t1 WHERE c1 IN (?)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( ?)""",
  """SELECT c1 FROM t1 WHERE c1 IN (? )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( ? )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n? )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( ?\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n?\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (?,?)""",
  """SELECT c1 FROM t1 WHERE c1 IN (?,?,?)""",
  """SELECT c1 FROM t1 WHERE c1 IN (?, ?,?, ? )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( ?,?)""",
  """SELECT c1 FROM t1 WHERE c1 IN (? ,?)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( ? ,?)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n:1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n:1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1,:2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1,:2,:3)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1, :2, :3, :4 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :1,:2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:1 ,:2)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :1 ,:2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :v1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :v1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n:v1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :v1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n:v1\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1,:v2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1,:v2,:v3)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1, :v2, :v3, :v4 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :v1,:v2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (:v1 ,:v2)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( :v1 ,:v2)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %s )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n%s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %s\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n%s\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s,%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s,%s,%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s, %s,%s , %s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %s,%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%s ,%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %s ,%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n%(v1)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s\n)""",
  """SELECT c1 FROM t1 WHERE c1 IN (\n%(v1)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s,%(v2)s,%(v3)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s, %(v2)s, %(v3)s , %(v4)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s ,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s ,%(v2)s)""",
  """ SELECT c1 FROM t1 WHERE c1 IN (1)""",
  """  SELECT c1 FROM t1 WHERE c1 IN (1)""",
  """ \n SELECT c1 FROM t1 WHERE c1 IN (1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1) """,
  """SELECT c1 FROM t1 WHERE c1 IN (1)  """,
  """SELECT c1 FROM t1 WHERE c1 IN (1) \n """,
  """SELECT  c1 FROM t1 WHERE c1 IN (1)""",
  """SELECT \n c1 FROM t1 WHERE c1 IN (1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (  1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( \n 1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN (1  )""",
  """SELECT c1 FROM t1 WHERE c1 IN (1 \n )""",
  """SELECT c1 FROM t1 WHERE c1 IN (""" + (50000*"""%s,""") + """%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (""" + (50000*""":1,""") + """%s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (""" + (50000*"""%(name)s,""") + """%s)""",
]

class DummySQLDatabase(object):
    database_name = 'Postgres'
    quoting_style = 'single'
    explain_query = None
    explain_stmts = ()

DUMMY_DATABASE = DummySQLDatabase()

class TestDatabase(unittest.TestCase):

    def test_parse_general_statements(self):
        for expected_result, sql in GENERAL_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    def test_parse_comment_statements(self):
        for expected_result, sql in COMMENT_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    def test_parse_select_statements(self):
        for expected_result, sql in SELECT_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            if expected_result != actual_result:
                print('XXX', expected_result == actual_result, sql)
            self.assertEqual(expected_result, actual_result)

    def test_parse_delete_tests(self):
        for expected_result, sql in DELETE_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    def test_parse_insert_tests(self):
        for expected_result, sql in INSERT_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    def test_parse_update_tests(self):
        for expected_result, sql in UPDATE_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    #def test_parse_create_tests(self):
    #    for expected_result, sql in CREATE_PARSE_TESTS:
    #        statement = SQLStatement(sql, DUMMY_DATABASE)
    #        actual_result = statement.target, statement.operation
    #        self.assertEqual(expected_result, actual_result)

    #def test_parse_call_tests(self):
    #    for expected_result, sql in CALL_PARSE_TESTS:
    #        statement = SQLStatement(sql, DUMMY_DATABASE)
    #        actual_result = statement.target, statement.operation
    #        self.assertEqual(expected_result, actual_result)

    #def test_parse_exec_tests(self):
    #    for expected_result, sql in EXEC_PARSE_TESTS:
    #        statement = SQLStatement(sql, DUMMY_DATABASE)
    #        actual_result = statement.target, statement.operation
    #        self.assertEqual(expected_result, actual_result)

    #def test_parse_alter_tests(self):
    #    for expected_result, sql in ALTER_PARSE_TESTS:
    #        statement = SQLStatement(sql, DUMMY_DATABASE)
    #        actual_result = statement.target, statement.operation
    #        self.assertEqual(expected_result, actual_result)

    def test_parse_show_tests(self):
        for expected_result, sql in SHOW_PARSE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.target, statement.operation
            self.assertEqual(expected_result, actual_result)

    #def test_parse_set_tests(self):
    #    for expected_result, sql in SET_PARSE_TESTS:
    #        statement = SQLStatement(sql, DUMMY_DATABASE)
    #        actual_result = statement.target, statement.operation
    #        self.assertEqual(expected_result, actual_result)

    def test_obfuscate_numeric_literals(self):
        sql = 'SELECT * FROM t1 WHERE t2.c3 = 1 AND 2 = 3'
        statement = SQLStatement(sql, DUMMY_DATABASE)
        expected_result = 'SELECT * FROM t1 WHERE t2.c3 = ? AND ? = ?'
        actual_result = statement.obfuscated
        self.assertEqual(expected_result, actual_result)

    def test_obfuscate_integer_word_boundaries(self):
        sql = 'A1 #2 ,3 .4 (5) =6 <7 /9 B9C'
        statement = SQLStatement(sql, DUMMY_DATABASE)
        expected_result = 'A1 #? ,? .? (?) =? <? /? B9C'
        actual_result = statement.obfuscated
        self.assertEqual(expected_result, actual_result)

    def test_obfuscate_string_literals(self):
        sql = "INSERT INTO X values('', 'a''b c',0, 1 , 'd''e f''s h')"
        statement = SQLStatement(sql, DUMMY_DATABASE)
        expected_result = "INSERT INTO X values(?, ?,?, ? , ?)"
        actual_result = statement.obfuscated
        self.assertEqual(expected_result, actual_result)

    def test_obfuscate_table_and_column_names(self):
        sql = 'SELECT "t"."c" FROM "t" WHERE "t"."c" = \'value\' LIMIT 1'
        statement = SQLStatement(sql, DUMMY_DATABASE)
        expected_result = 'SELECT "t"."c" FROM "t" WHERE "t"."c" = ? LIMIT ?'
        actual_result = statement.obfuscated
        self.assertEqual(expected_result, actual_result)

    def test_obfuscate_mysql_table_and_column_names(self):
        sql = 'SELECT `t`.`c` FROM `t` WHERE `t`.`c` = \'value\' LIMIT 1'
        statement = SQLStatement(sql, DUMMY_DATABASE)
        expected_result = 'SELECT `t`.`c` FROM `t` WHERE `t`.`c` = ? LIMIT ?'
        actual_result = statement.obfuscated
        self.assertEqual(expected_result, actual_result)

    def test_normalize_sql_tests(self):
        expected_result = 'SELECT c1 FROM t1 WHERE c1 IN(?)'
        for sql in SQL_NORMALIZE_TESTS:
            statement = SQLStatement(sql, DUMMY_DATABASE)
            actual_result = statement.normalized
            self.assertEqual(expected_result, actual_result)
            self.assertEqual(hash(expected_result), hash(actual_result))

class TestDatabaseHelpers(unittest.TestCase):

    def test_explain_plan_results(self):
        columns = ['QUERY PLAN']
        rows = [{'QUERY PLAN': 'Index scan'}]
        expected = [('Index scan',)]
        actual = _query_result_dicts_to_tuples(columns, rows)
        self.assertEqual(expected, actual)

    def test_preserve_order(self):
        columns = ['first', 'middle', 'last']
        rows = [{'last': 'c', 'middle': 'b', 'first': 'a'},
                {'middle': '2', 'last': '3', 'first': '1'}]
        expected = [('a', 'b', 'c'), ('1', '2', '3')]
        actual = _query_result_dicts_to_tuples(columns, rows)
        self.assertEqual(expected, actual)

    def test_empty_columns_and_rows(self):
        columns = None
        rows = []
        expected = None
        actual = _query_result_dicts_to_tuples(columns, rows)
        self.assertEqual(expected, actual)

if __name__ == "__main__":
    unittest.main()
