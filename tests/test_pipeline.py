import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ev_analysis.pipeline import run
from ev_analysis.contracts import Config


def test_pipeline_saves_reproducible_artifacts_and_preserves_source(tmp_path) -> None:
    source = tmp_path / 'source.csv'
    source.write_text('timestamp,car_velocity,car_trip,car_voltage,car_current,power,gps_1,gps_2,timestamp_original,retroceso_detectado,segmento\n'
                      '2025-01-01 00:00:00,36,0,50,2,100,4.95,-74.02,2025-01-01 00:00:00,False,1\n'
                      '2025-01-01 00:00:02,36,.02,50,2,100,4.95,-74.02,2025-01-01 00:00:02,False,1\n', encoding='utf-8')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    a, b = tmp_path / 'a', tmp_path / 'b'
    run(source, a, Config(window_s=2))
    run(source, b, Config(window_s=2))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    for folder in ('figures', 'tables', 'reports'):
        files = list((a / folder).glob('*'))
        assert files
        for file in files:
            assert file.read_bytes() == (b / folder / file.name).read_bytes()
            if file.suffix == '.svg':
                assert ET.parse(file).getroot().tag.endswith('svg')
    assert json.loads((a / 'reports' / 'manifest.json').read_text())['source_sha256'] == before
    assert (a / 'tables' / 'data_dictionary.csv').exists()
    assert (a / 'tables' / 'interval_ledger.csv').exists()
    assert (a / 'tables' / 'sample_quality_flags.csv').exists()
    assert (a / 'reports' / 'findings.md').exists()
