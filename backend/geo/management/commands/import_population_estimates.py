import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geo.models import Jcode, PopulationEstimate

ID_COLUMN = 'censusplacecode'

# CSV header (lowercased) -> Jcode field. These describe the place itself
# (Census geography/methodology codes) and don't vary by year, so they're
# stored on Jcode rather than repeated on every PopulationEstimate row.
JCODE_META_COLUMNS = {
    'sumlev': 'sumlev',
    'state': 'state_fips',
    'county': 'county_fips',
    'place': 'place_fips',
    'cousub': 'cousub_fips',
    'concit': 'concit_fips',
    'primgeo_flag': 'primgeo_flag',
    'funcstat': 'funcstat',
}

POPESTIMATE_RE = re.compile(r'^popestimate(\d{4})$')
ESTIMATESBASE_RE = re.compile(r'^estimatesbase(\d{4})$')


class Command(BaseCommand):
    help = (
        'Import/update PopulationEstimate records (and Jcode geography metadata) '
        'from all CSV files in a directory. Rows whose CensusPlaceCode has no '
        'matching Jcode are skipped.'
    )

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing population estimate CSV files')

    def handle(self, *args, **options):
        directory = Path(options['directory'])
        if not directory.is_dir():
            raise CommandError(f'{directory} is not a directory')

        csv_files = sorted(directory.glob('*.csv'))
        if not csv_files:
            self.stdout.write(self.style.WARNING(f'No CSV files found in {directory}'))
            return

        total_created = total_updated = total_missing = 0
        for csv_file in csv_files:
            created, updated, missing = self._import_file(csv_file)
            total_created += created
            total_updated += updated
            total_missing += missing
            self.stdout.write(
                f'{csv_file.name}: {created} created, {updated} updated, '
                f'{missing} row(s) skipped (unknown jcode)'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Done. {total_created} created, {total_updated} updated, '
            f'{total_missing} skipped across {len(csv_files)} file(s).'
        ))

    def _import_file(self, csv_file):
        with csv_file.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            lookup, id_col, year_cols = self._build_header_map(reader.fieldnames, csv_file)

            created = updated = missing = 0
            with transaction.atomic():
                for row in reader:
                    place_id = row[id_col].strip()
                    if not place_id:
                        continue

                    try:
                        jcode = Jcode.objects.get(id=place_id)
                    except Jcode.DoesNotExist:
                        missing += 1
                        continue

                    self._update_jcode_meta(jcode, row, lookup)

                    for header_name, year, series in year_cols:
                        raw_value = row[header_name].strip()
                        if raw_value == '':
                            continue
                        _, was_created = PopulationEstimate.objects.update_or_create(
                            jcode=jcode,
                            year=year,
                            series=series,
                            defaults={'population': int(raw_value)},
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1
        return created, updated, missing

    def _update_jcode_meta(self, jcode, row, lookup):
        changed_fields = []
        for header_key, field_name in JCODE_META_COLUMNS.items():
            if header_key not in lookup:
                continue
            raw_value = row[lookup[header_key]].strip()
            if raw_value == '':
                continue
            value = raw_value if field_name == 'funcstat' else int(raw_value)
            if getattr(jcode, field_name) != value:
                setattr(jcode, field_name, value)
                changed_fields.append(field_name)
        if changed_fields:
            jcode.save(update_fields=changed_fields)

    def _build_header_map(self, fieldnames, csv_file):
        if not fieldnames:
            raise CommandError(f'{csv_file.name} has no header row')
        lookup = {name.strip().lower(): name for name in fieldnames}
        if ID_COLUMN not in lookup:
            raise CommandError(f'{csv_file.name} is missing required column: CensusPlaceCode')

        year_cols = []
        for name in fieldnames:
            key = name.strip().lower()
            match = POPESTIMATE_RE.match(key)
            if match:
                year_cols.append((name, int(match.group(1)), PopulationEstimate.Series.ESTIMATE))
                continue
            match = ESTIMATESBASE_RE.match(key)
            if match:
                year_cols.append((name, int(match.group(1)), PopulationEstimate.Series.BASE))
        if not year_cols:
            raise CommandError(f'{csv_file.name} has no POPESTIMATE/ESTIMATESBASE year columns')

        return lookup, lookup[ID_COLUMN], year_cols
