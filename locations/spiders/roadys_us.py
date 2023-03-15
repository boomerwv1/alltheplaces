import scrapy
from scrapy.http import JsonRequest

from locations.categories import Categories, Extras, Fuel, PaymentMethods, apply_category, apply_yes_no
from locations.dict_parser import DictParser
from locations.hours import DAYS, OpeningHours


class RoadysUSSpider(scrapy.Spider):
    name = "roadys_us"
    item_attributes = {"brand": "Roady’s Truck Stops", "brand_wikidata": "Q7339701"}
    allowed_domains = ["roadys.com"]
    start_urls = ["https://api-v2.roadys.com/locations?show_all=true"]

    def start_requests(self):
        # Authorization Bearer is generated by packed static JavaScript and does not appear to change.
        headers = {
            "Authorization": "Bearer P7I6obDhgTejlPBV82F1W0cw1Qi7UeP9W40pS7d0xKB",
        }
        yield JsonRequest(url=self.start_urls[0], headers=headers)

    def parse(self, response):
        for location in response.json()["locations"]:
            item = DictParser.parse(location)
            item["ref"] = location["location_id"]
            item["name"] = location["location_name"]
            item["street_address"] = item.pop("addr_full")
            apply_category(Categories.FUEL_STATION, item)
            for amenity in location["amenities"]:
                match amenity["name"]:
                    case "Convenience Store":
                        if amenity["status"][0]:
                            apply_category(Categories.SHOP_CONVENIENCE, item)
                    case "Store Hours" | "Open 24/7":
                        # There are numerous locations which aren't 24/7, but the
                        # source data is extremely messy and not worth the effort
                        # to try and parse. However it's still worthwhile noting
                        # a location is 24/7 as this is easy to parse (and common).
                        if amenity["status"][0] == "24/7" or amenity["status"][0] is True:
                            item["opening_hours"] = OpeningHours()
                            item["opening_hours"].add_days_range(DAYS, "00:00", "23:59")
                    case "Dine-In Restaurant" | "Dine-In Restauraunt":
                        if amenity["status"][0]:
                            apply_category(Categories.RESTAURANT, item)
                        apply_yes_no(Extras.INDOOR_SEATING, item, amenity["status"][0], False)
                    case "Seats":
                        item["extras"].update({"capacity:seats": amenity["status"][0]})
                    case "Lounge":
                        apply_yes_no(Extras.INDOOR_SEATING, item, amenity["status"][0], False)
                    case "Internet (Wireless)":
                        apply_yes_no(Extras.WIFI, item, amenity["status"][0], False)
                    case "Public Copier":
                        apply_yes_no(Extras.COPYING, item, amenity["status"][0], False)
                    case "Public Fax Number" | "Public Fax":
                        apply_yes_no(Extras.FAXING, item, amenity["status"][0], False)
                    case "Showers":
                        apply_yes_no(Extras.SHOWERS, item, amenity["status"][0], False)
                    case "DEF Available":
                        apply_yes_no(Fuel.ADBLUE, item, amenity["status"][0], False)
                    case "Propane (Bottled)" | "Propane (Metered)":
                        apply_yes_no(Fuel.PROPANE, item, amenity["status"][0], False)
                    case "Diesel Pumps":
                        item["extras"].update({"capacity:hgv": amenity["status"][0]})
                    case "# of Gas Pumps":
                        item["extras"].update({"capacity:motorcar": amenity["status"][0]})
                    case "Fuel Service":
                        if "Self" in amenity["status"][0]:
                            item["extras"].update({"self_service": "yes"})
                    case "Truck Wash":
                        apply_yes_no(Extras.TRUCK_WASH, item, amenity["status"][0], False)
                    case "ATM(s)":
                        apply_yes_no(Extras.ATM, item, amenity["status"][0], False)
                    case "Accepted Credit Cards":
                        apply_yes_no(PaymentMethods.VISA, item, "Visa" in amenity["status"], False)
                        apply_yes_no(PaymentMethods.MASTER_CARD, item, "MasterCard" in amenity["status"], False)
                        apply_yes_no(
                            PaymentMethods.AMERICAN_EXPRESS, item, "American Express" in amenity["status"], False
                        )
                        apply_yes_no(PaymentMethods.DISCOVER_CARD, item, "Discover" in amenity["status"], False)
                        apply_yes_no(PaymentMethods.DINERS_CLUB, item, "Diners Club" in amenity["status"], False)

            yield item