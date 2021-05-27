'''
Management command to set as None any CourseDailyMetrics.average_progress values 
if produced by a backfill.

We do this because progress or any other value generated by examining StudentModule
values will not be correct if done for a previous date, until or unless Figures uses
StudentModuleHistory or Persistent Grades to examine db-stored student grade or SM values.
'''

from __future__ import absolute_import, print_function

from datetime import timedelta
from textwrap import dedent

from django.db.models import Count, F, Max, Min

from figures.models import CourseDailyMetrics

from . import BaseBackfillCommand


class Command(BaseBackfillCommand):
    '''Set all CourseDailyMetrics average_progress values to None where CDM was created
    more than one day after the date_for value.  See module docstring for rationale.
    '''

    help = dedent(__doc__).strip()

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help=('Dry run. Output but don\'t save changes')
        )
        super(Command, self).add_arguments(parser)

    def handle(self, *args, **options):
        '''
        '''
        site = self.get_sites(options['site'])[0]

        print('FIGURES: Repairing backfilled CDM.average_progress for site {}'.format(site))

        backfills = CourseDailyMetrics.objects.filter(
            site=site, created__gt=F('date_for') + timedelta(days=2)
        ).annotate(courses_count=Count('course_id', distinct=True))

        num_backfills = backfills.count()

        logmsg = (
            'FIGURES: Found {count} records from dates between {date_start} and {date_end} from courses:\n\n{courses}'
            'to update with None values for average_progress'.format(
                count=num_backfills,
                date_start=backfills.earliest('date_for').date_for,
                date_end=backfills.latest('date_for').date_for,
                courses=', \n'.join(set(backfills.values_list('course_id', flat=True)))
            )
        )
        print(logmsg)

        if not options['dry_run']:
            print('FIGURES: set average_progress to None for {} CourseDailyMetrics records'.format(num_backfills))
            backfills.update(average_progress=None)
