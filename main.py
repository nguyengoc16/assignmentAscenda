from dataclasses import dataclass, field
import json
import argparse
import requests


@dataclass
class Location:
    lat: float = None
    lng: float = None
    address: str = None
    city: str = None
    country: str = None


@dataclass
class Amenities:
    general: list = field(default_factory=list)
    room: list = field(default_factory=list)


@dataclass
class Image:
    link: str
    description: str


@dataclass
class Images:
    rooms: list[Image] = field(default_factory=list)
    site: list[Image] = field(default_factory=list)
    amenities: list[Image] = field(default_factory=list)


@dataclass
class Hotel:
    id: str
    source:str
    destination_id: int
    name: str
    location: Location = field(default_factory=Location)
    description: str = ""
    amenities: Amenities = field(default_factory=Amenities)
    images: Images = field(default_factory=Images)
    booking_conditions: list[str] = field(default_factory=list)


class BaseSupplier:
    @staticmethod
    def endpoint():
        """URL to fetch supplier data"""

    @staticmethod
    def parse(data: dict) -> Hotel:
        """Parse supplier-provided data into Hotel object"""

    def fetch(self):
        url = self.endpoint()
        resp = requests.get(url)
        return [self.parse(dto) for dto in resp.json()]


class Acme(BaseSupplier):
    @staticmethod
    def endpoint():
        return 'https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/acme'

    @staticmethod
    def parse(dto: dict) -> Hotel:
        return Hotel(
            id=dto['Id'],
            source='Acme',
            destination_id=dto['DestinationId'],
            name=dto['Name'],
            description=dto.get('Description', ""),
            location=Location(
                lat=dto.get('Latitude'),
                lng=dto.get('Longitude'),
                address=f"{dto.get('Address', '').strip()}, {dto.get('PostalCode', '').strip()}",
                city=dto.get('City'),
                country=dto.get('Country')
            ),
            # amenities=Amenities(
            #     general=[facility.strip().lower() for facility in dto.get('Facilities', [])]
            # )
        )


class Patagonia(BaseSupplier):
    @staticmethod
    def endpoint():
        return 'https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/patagonia'

    @staticmethod
    def parse(dto: dict) -> Hotel:
        return Hotel(
            id=dto['id'],
            source='Patagonia',
            destination_id=dto['destination'],
            name=dto['name'],
            description=dto.get('info', ""),
            location=Location(
                lat=dto.get('lat'),
                lng=dto.get('lng'),
                address=dto.get('address')
            ),
            # amenities=Amenities(
            #     room=[amenity.lower() for amenity in (dto.get('amenities') or [])]
            # ),
            images=Images(
                rooms=[Image(link=image['url'], description=image['description']) for image in dto['images'].get('rooms', [])],
                amenities=[Image(link=image['url'], description=image['description']) for image in dto['images'].get('amenities', [])]
            )
        )


class Paperflies(BaseSupplier):
    @staticmethod
    def endpoint():
        return 'https://5f2be0b4ffc88500167b85a0.mockapi.io/suppliers/paperflies'

    @staticmethod
    def parse(dto: dict) -> Hotel:
        location_data = dto.get('location', {})
        return Hotel(
            id=dto['hotel_id'],
            source='Paperflies',
            destination_id=dto['destination_id'],
            name=dto['hotel_name'],
            description=dto.get('details', ""),
            location=Location(
                address=location_data.get('address'),
                country=location_data.get('country')
            ),
            amenities=Amenities(
                general=[amenity.lower() for amenity in dto.get('amenities', {}).get('general', [])],
                room=[amenity.lower() for amenity in dto.get('amenities', {}).get('room', [])]
            ),
            images=Images(
                rooms=[Image(link=image['link'], description=image['caption']) for image in dto['images'].get('rooms', [])],
                site=[Image(link=image['link'], description=image['caption']) for image in dto['images'].get('site', [])]
            ),
            booking_conditions=dto.get('booking_conditions', [])
        )


class HotelsService:
    def __init__(self):
        self.hotels = {}

    def merge_and_save(self, data):
        for hotel in data:
            if hotel.id not in self.hotels:
                self.hotels[hotel.id] = hotel
            else:
                self._merge(self.hotels[hotel.id], hotel)

    def _merge(self, base: Hotel, incoming: Hotel):
                
        if base.location and incoming.location:
            for field in base.location.__dataclass_fields__:
                base_value = getattr(base.location, field)
                incoming_value = getattr(incoming.location, field)
                
                # Special handling for country to check if it's from Paperflies
                if field == 'country' and incoming_value and incoming.source == 'Paperflies':
                    setattr(base.location, field, incoming_value)
                # For other fields, keep existing logic
                elif not base_value and incoming_value:
                    setattr(base.location, field, incoming_value)
        elif not base.location:
            # If base location is None, copy the whole incoming location
            base.location = incoming.location

        base.description = base.description or incoming.description
        base.amenities.general = list(set(base.amenities.general + incoming.amenities.general))
        base.amenities.room = list(set(base.amenities.room + incoming.amenities.room))
        base.images.rooms = list({(image.link, image.description): image for image in base.images.rooms + incoming.images.rooms}.values())
        base.images.site = list({(image.link, image.description): image for image in base.images.site + incoming.images.site}.values())
        base.images.amenities.extend(incoming.images.amenities)
        base.booking_conditions = list(set(base.booking_conditions + incoming.booking_conditions))
        if hasattr(base, "source"):
            del base.source

    def find(self, hotel_ids=None, destination_ids=None): 
        hotels_data = list(self.hotels.values()) 
        results = [] 
        if hotel_ids is None and destination_ids is not None: 
            results = [hotel for hotel in hotels_data if hotel.destination_id in destination_ids] 
            return results 
        if destination_ids is None and hotel_ids is not None: 
            results = [hotel for hotel in hotels_data if hotel.id in hotel_ids] 
            return results 
        if destination_ids is None and hotel_ids is not None: 
            return hotels_data 
        
        for i in range(len(hotel_ids)): 
            hotel_id = hotel_ids[i] 
            destination_id = destination_ids[i] if i < len(destination_ids) else None 
            for hotel in hotels_data: 
                if hotel.id == hotel_id and (destination_id is None or hotel.destination_id == destination_id):
                    results.append(hotel) 
                    break 
                return results


    # def find(self, hotel_ids=None, destination_ids=None):
    #     hotels_data = list(self.hotels.values())
    #     results = []
    #     if len(hotel_ids) >= len(destination_ids):
    #         for i in range(0, len(destination_ids)):
    #             if hotels_data.
                
        


    #     # if hotel_ids:
    #     #     results = [hotel for hotel in results if hotel.id in hotel_ids]
    #     # if destination_ids:
    #     #     results = [hotel for hotel in results if hotel.destination_id in destination_ids]
    #     return results


def fetch_hotels(hotel_ids, destination_ids):
    suppliers = [Acme(), Patagonia(), Paperflies()]
    all_supplier_data = []
    for supplier in suppliers:
        all_supplier_data.extend(supplier.fetch())

    svc = HotelsService()
    svc.merge_and_save(all_supplier_data)

    hotel_ids = hotel_ids.split(",") if hotel_ids != "none" else None
    destination_ids = list(map(int, destination_ids.split(","))) if destination_ids != "none" else None
    filtered_hotels = svc.find(hotel_ids, destination_ids)
    return json.dumps([hotel.__dict__ for hotel in filtered_hotels], default=lambda o: o.__dict__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("hotel_ids", type=str, help="Hotel IDs")
    parser.add_argument("destination_ids", type=str, help="Destination IDs")
    args = parser.parse_args()
    print(fetch_hotels(args.hotel_ids, args.destination_ids))


if __name__ == "__main__":
    main()
