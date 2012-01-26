import unittest

from newrelic.core.database_utils import obfuscated_sql, parsed_sql

SQL_PARSE_TESTS = [
  (
    # Empty.
    (None, None),
    ""
  ),
  (
    # Empty (whitespace).
    (None, None),
    " "
  ),
  (
    # Invalid.
    (None, None),
    """select"""
  ),

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
    # Call.
    ('foo', 'call'),
    """CALL FOO(1, 2) """
  ),
  (
    # Call.
    ('foo', 'call'),
    """CALL FOO 1 2 """
  ),

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
    # Set.
    ('language', 'set'),
    """SET LANGUAGE Australian"""
  ),
  (
    # Set.
    ('auto commit', 'set'),
    """SET AUTO COMMIT ON"""
  ),
  (
    # Set.
    ('transaction isolation level', 'set'),
    """SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"""
  ),
]

SQL_COLLAPSE_TESTS = [
  """SELECT c1 FROM t1 WHERE c1 IN (1)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1)""",
  """SELECT c1 FROM t1 WHERE c1 IN (1 )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( 1 )""",
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
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s,%(v2)s,%(v3)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s, %(v2)s, %(v3)s , %(v4)s )""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN (%(v1)s ,%(v2)s)""",
  """SELECT c1 FROM t1 WHERE c1 IN ( %(v1)s ,%(v2)s)""",
]

class TestDatabase(unittest.TestCase):
    def test_obfuscator_obfuscates_numeric_literals(self):
        select = "SELECT * FROM table WHERE table.column = 1 AND 2 = 3"
        self.assertEqual("SELECT * FROM table WHERE table.column = ? AND ? = ?",
                         obfuscated_sql('pyscopg2', select))
        insert = "INSERT INTO table VALUES (1,2, 3 ,  4)"
        self.assertEqual("INSERT INTO table VALUES (?,?, ? ,  ?)",
                         obfuscated_sql('psycopg2', insert))

    def test_obfuscator_obfuscates_string_literals(self):
        insert = "INSERT INTO X values('', 'jim''s ssn',0, 1 , 'jim''s son''s son')"
        self.assertEqual("INSERT INTO X values(?, ?,?, ? , ?)",
                         obfuscated_sql('psycopg2', insert))

    def test_obfuscator_does_not_obfuscate_table_or_column_names(self):
        select = 'SELECT "table"."column" FROM "table" WHERE "table"."column" = \'value\' LIMIT 1'
        self.assertEqual('SELECT "table"."column" FROM "table" WHERE "table"."column" = ? LIMIT ?',
                         obfuscated_sql('psycopg2', select))

    def test_mysql_obfuscation(self):
        select = 'SELECT `table`.`column` FROM `table` WHERE `table`.`column` = \'value\' AND `table`.`other_column` = "other value" LIMIT 1'
        self.assertEqual('SELECT `table`.`column` FROM `table` WHERE `table`.`column` = ? AND `table`.`other_column` = ? LIMIT ?',
                         obfuscated_sql('MySQLdb', select))

    def test_obfuscator_does_not_obfuscate_trailing_integers(self):
        select = "SELECT * FROM table1 WHERE table2.column3 = 1 AND 2 = 3"
        self.assertEqual("SELECT * FROM table1 WHERE table2.column3 = ? AND ? = ?",
                         obfuscated_sql('pyscopg2', select))

    def test_obfuscator_does_not_obfuscate_integer_word_boundaries(self):
        select = "A1 #2 ,3 .4 (5) =6 <7 /9 B9C"
        self.assertEqual("A1 #? ,? .? (?) =? <? /? B9C",
                         obfuscated_sql('pyscopg2', select))

    def test_obfuscator_collapses_in_clause_literal(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (1,2,3)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

    def test_obfuscator_collapses_in_clause_parameterised(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (%s,%s,%s)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

    def test_obfuscator_collapses_in_clause_very_large(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (" + \
                (50000 * "%s,") + "%s)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

    def test_obfuscator_very_large_in_clause(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (" + \
                (50000 * "%s,") + "%s)"
        self.assertEqual(('table1', 'select'), parsed_sql('pyscopg2', select))

    def test_parse_sql_tests(self):
        for result, sql in SQL_PARSE_TESTS:
            self.assertEqual(result, parsed_sql('pyscopg2', sql))

    def test_collapse_sql_tests(self):
        for sql in SQL_COLLAPSE_TESTS:
            self.assertEqual("SELECT c1 FROM t1 WHERE c1 IN (?)",
                             obfuscated_sql('psycopg2', sql, collapsed=True))

if __name__ == "__main__":
    unittest.main()
