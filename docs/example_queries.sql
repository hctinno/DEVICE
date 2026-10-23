-- All statements below are read-only inventory queries, not device control.

-- 1. Browse every source record with normalized manufacturer and category.
SELECT equipment_id, register_no, name, manufacturer, model_name,
       serial_number, category, source_status_hint
FROM v_equipment_inventory ORDER BY register_no;

-- 2. Manufacturer counts are source record counts, not verified active assets.
SELECT manufacturer, equipment_records, model_count
FROM v_manufacturer_summary ORDER BY equipment_records DESC;

-- 3. Group future documentation/driver research by manufacturer + model.
SELECT manufacturer, model_name, equipment_records, research_status,
       suggested_categories, programming_manual_url, sdk_url
FROM v_model_research_queue ORDER BY equipment_records DESC;

-- 4. Do not identify an individual unit by its serial number alone.
SELECT duplicate_group_id, match_type, member_count
FROM duplicate_groups WHERE match_type = 'manufacturer_model_serial';

-- 5. Candidate manufacturer corrections are not applied to the inventory.
SELECT raw_label, suggested_canonical_name, rationale
FROM manufacturer_aliases WHERE review_required=1;

-- 6. Review unresolved model identity before selecting a driver.
SELECT equipment_id, name, manufacturer_raw, model_raw, serial_raw, source_row
FROM v_equipment_inventory WHERE model_id IS NULL;

-- 7. Search historical registration numbers; do not label them current IDs.
SELECT e.equipment_id,e.name,i.identifier_value,i.source_excerpt
FROM equipment_identifiers i JOIN equipment e USING(equipment_id)
WHERE i.identifier_type='legacy_registration';

-- 8. Raw source data is retained without treating note content as instructions.
SELECT e.equipment_id,r.sheet_name,r.row_number,r.cells_json
FROM equipment e JOIN source_rows r USING(source_row_id)
WHERE e.equipment_id='EQ-000001';
