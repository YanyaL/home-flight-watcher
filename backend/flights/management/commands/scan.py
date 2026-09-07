from django.core.management.base import BaseCommand

from flights.services.airports import airline_name, city_of
from flights.services.scanner import run_scan


class Command(BaseCommand):
    help = "Scan configured flight routes once and store results"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-booking-links",
            action="store_true",
            help="Skip SerpAPI booking_token lookups to save quota",
        )

    def handle(self, *args, **options):
        summary = run_scan(attach_bookings=not options["no_booking_links"])
        self.stdout.write(
            self.style.SUCCESS(
                f"provider={summary.provider} raw={summary.offer_count} kept={summary.kept_count}"
            )
        )
        for title, offer in (("最合适", summary.best), ("最便宜", summary.cheapest)):
            if not offer:
                continue
            airlines = "+".join(airline_name(code) for code in offer.airlines)
            self.stdout.write(
                f"{title}: {city_of(offer.origin)}→{city_of(offer.dest)} "
                f"{offer.depart_date} {offer.price:.0f} {offer.currency} "
                f"{offer.stops}停 / {offer.duration_min // 60}h{offer.duration_min % 60:02d}m "
                f"{airlines} 得分 {offer.score}"
            )
            if offer.booking_url:
                self.stdout.write(f"  购买: {offer.booking_url[:120]}...")
