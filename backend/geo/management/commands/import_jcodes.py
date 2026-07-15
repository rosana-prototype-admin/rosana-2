import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geo.models import Jcode

# Maps lowercased CSV header -> Jcode field. 'ST' (abbreviation) is unused;
# the model stores the full state name from STName/STNAME.
REQUIRED_COLUMNS = {
    'censusplacecode': 'id',
    'stname': 'state',
    'county': 'county',
    'placenamelong': 'place_name_long',
    'placenameshort': 'place_name_short',
    'censusplacename': 'census_place_name',
}


class Command(BaseCommand):
    help = 'Import/update Jcode records from all CSV files in a directory.'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing jcode CSV files')

    def handle(self, *args, **options):
        directory = Path(options['directory'])
        if not directory.is_dir():
            raise CommandError(f'{directory} is not a directory')

        csv_files = sorted(directory.glob('*.csv'))
        if not csv_files:
            self.stdout.write(self.style.WARNING(f'No CSV files found in {directory}'))
            return

        total_created = 0
        total_updated = 0
        for csv_file in csv_files:
            created, updated = self._import_file(csv_file)
            total_created += created
            total_updated += updated
            self.stdout.write(f'{csv_file.name}: {created} created, {updated} updated')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {total_created} created, {total_updated} updated across {len(csv_files)} file(s).'
        ))

    def _import_file(self, csv_file):
        with csv_file.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            header_map = self._build_header_map(reader.fieldnames, csv_file)

            created = updated = 0
            with transaction.atomic():
                for row in reader:
                    place_id = row[header_map['id']].strip()
                    if not place_id:
                        continue
                    defaults = {
                        'state': row[header_map['state']].strip(),
                        'county': row[header_map['county']].strip(),
                        'place_name_long': row[header_map['place_name_long']].strip(),
                        'place_name_short': row[header_map['place_name_short']].strip(),
                        'census_place_name': row[header_map['census_place_name']].strip(),
                    }
                    _, was_created = Jcode.objects.update_or_create(id=place_id, defaults=defaults)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
        return created, updated

    def _build_header_map(self, fieldnames, csv_file):
        if not fieldnames:
            raise CommandError(f'{csv_file.name} has no header row')
        lookup = {name.strip().lower(): name for name in fieldnames}
        header_map = {}
        missing = []
        for key, field in REQUIRED_COLUMNS.items():
            if key not in lookup:
                missing.append(key)
            else:
                header_map[field] = lookup[key]
        if missing:
            raise CommandError(f'{csv_file.name} is missing required column(s): {", ".join(missing)}')
        return header_map
