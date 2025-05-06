import xml.etree.ElementTree as ET
import json
import os

def parse_xml(xml_file):
    '''Парсинг xml-файла, извлекаем данные о классах их их связях'''
    tree = ET.parse(xml_file)
    root = tree.getroot()
    classes = {}
    aggregations = []

    for class_elem in root.findall('Class'):
        class_name = class_elem.get('name')
        is_root = class_elem.get('isRoot') == 'true'
        documentation = class_elem.get('documentation', '')
        attributes = [
            {
                'name': attr.get('name'),
                'type': attr.get('type')
            } for attr in class_elem.findall('Attribute')
        ]
        classes[class_name] = {
            'isRoot': is_root,
            'documentation': documentation,
            'attributes': attributes
        }

    for agg in root.findall('Aggregation'):
        aggregations.append({
            'source': agg.get('source'),
            'target': agg.get('target'),
            'sourceMultiplicity': agg.get('sourceMultiplicity'),
            'targetMultiplicity': agg.get('targetMultiplicity')
        })

    return classes, aggregations

def generate_config_xml(classes, aggregations):
    '''Генерация xml-файла на основании иерархии классов и их атрибутов'''
    root_class = next(c for c, v in classes.items() if v['isRoot'])
    xml_root = ET.Element(root_class)

    for attr in classes[root_class]['attributes']:
        attr_elem = ET.SubElement(xml_root, attr['name'])
        attr_elem.text = attr['type']

    def process_class(parent_elem, parent_class):
        child_aggs = [a for a in aggregations if a['target'] == parent_class]
        for agg in child_aggs:
            source_class = agg['source']
            source_elem = ET.SubElement(parent_elem, source_class)
            for attr in classes[source_class]['attributes']:
                attr_elem = ET.SubElement(source_elem, attr['name'])
                attr_elem.text = attr['type']
            process_class(source_elem, source_class)

    process_class(xml_root, root_class)
    return ET.tostring(xml_root, encoding='unicode', method='xml')

def generate_meta_json(classes, aggregations):
    '''Создаём json-файл с мета-информацией о классах'''
    meta = []
    for class_name, class_data in classes.items():
        entry = {
            'class': class_name,
            'documentation': class_data['documentation'],
            'isRoot': class_data['isRoot'],
            'parameters': []
        }
        for attr in class_data['attributes']:
            entry['parameters'].append({
                'name': attr['name'],
                'type': attr['type']
            })
        child_aggs = [a for a in aggregations if a['target'] == class_name]
        for agg in child_aggs:
            entry['parameters'].append({
                'name': agg['source'],
                'type': 'class'
            })
            multiplicity = agg['sourceMultiplicity']
            if '..' in multiplicity:
                entry['min'], entry['max'] = multiplicity.split('..')
            else:
                entry['min'] = entry['max'] = multiplicity
        if not child_aggs and not class_data['isRoot']:
            entry['min'] = '1'
            entry['max'] = '1'
        meta.append(entry)
    return meta

def generate_delta_json(config, patched_config):
    '''Генерация delta.json, который который показывает разницу между'''
    delta = {
        'additions': [],
        'deletions': [],
        'updates': []
    }
    for key, value in patched_config.items():
        if key not in config:
            delta['additions'].append({'key': key, 'value': value})
    for key in config:
        if key not in patched_config:
            delta['deletions'].append(key)
    for key in config:
        if key in patched_config and config[key] != patched_config[key]:
            delta['updates'].append({
                'key': key,
                'from': config[key],
                'to': patched_config[key]
            })
    return delta

def generate_res_patched_config(config, delta):
    '''Применение delta.json к config.json'''
    result = config.copy()
    for key in delta['deletions']:
        result.pop(key, None)
    for update in delta['updates']:
        result[update['key']] = update['to']
    for addition in delta['additions']:
        result[addition['key']] = addition['value']
    return result

def main():
    '''Создание папки для записи результата действия программы и генерация всех файлов'''
    output_dir = 'out'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    classes, aggregations = parse_xml('impulse_test_input.xml')

    config_xml = generate_config_xml(classes, aggregations)
    with open(os.path.join(output_dir, 'config.xml'), 'w') as f:
        f.write('<?xml version="1.0" ?>\n' + config_xml)

    meta_json = generate_meta_json(classes, aggregations)
    with open(os.path.join(output_dir, 'meta.json'), 'w') as f:
        json.dump(meta_json, f, indent=4)

    with open('config.json', 'r') as f:
        config = json.load(f)
    with open('patched_config.json', 'r') as f:
        patched_config = json.load(f)

    delta = generate_delta_json(config, patched_config)
    with open(os.path.join(output_dir, 'delta.json'), 'w') as f:
        json.dump(delta, f, indent=4)

    res_patched = generate_res_patched_config(config, delta)
    with open(os.path.join(output_dir, 'res_patched_config.json'), 'w') as f:
        json.dump(res_patched, f, indent=4)

if __name__ == "__main__":
    main()
