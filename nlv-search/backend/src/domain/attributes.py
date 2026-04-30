from enum import Enum


class Gender(str, Enum):
    """Gender values supported by the VMS face attribute filter."""

    male = "male"
    female = "female"


class Beard(str, Enum):
    """Beard attribute values for face filtering."""

    with_beard = "with_beard"
    without_beard = "without_beard"


class Glasses(str, Enum):
    """Glasses attribute values for face filtering."""

    with_glasses = "with_glasses"
    without_glasses = "without_glasses"


class Race(str, Enum):
    """Race attribute values returned by face analysis."""

    white = "white"
    black = "black"
    asian = "asian"
    indian = "indian"
    other = "other"
    middle_eastern = "middle_eastern"
    latino = "latino"


class Hat(str, Enum):
    """Hat attribute values for face filtering."""

    with_hat = "with_hat"
    without_hat = "without_hat"


class Mask(str, Enum):
    """Mask attribute values for face filtering."""

    with_mask = "with_mask"
    without_mask = "without_mask"


class VehicleColor(str, Enum):
    """Vehicle color values supported by the VMS vehicle filter."""

    White = "white"
    Yellow = "yellow"
    Orange = "orange"
    Red = "red"
    Green = "green"
    Blue = "blue"
    Brown = "brown"
    Gray = "gray"
    Black = "black"


class CarBrand(str, Enum):
    """Vehicle brand values supported by the VMS vehicle filter."""

    Audi = "AUDI"
    BMW = "BMW"
    Changan = "CHANGAN"
    Chery = "CHERY"
    Chevrolet = "CHEVROLET"
    Citroen = "CITROEN"
    DAF = "DAF"
    Exeed = "EXEED"
    Fiat = "FIAT"
    Ford = "FORD"
    GAZ = "GAZ"
    Geely = "GEELY"
    Haval = "HAVAL"
    Honda = "HONDA"
    Hyundai = "HYUNDAI"
    Iveco = "IVECO"
    Jaecoo = "JAECOO"
    Jeep = "JEEP"
    Jetour = "JETOUR"
    KAMAZ = "KAMAZ"
    Kia = "KIA"
    Lada = "LADA"
    Lexus = "LEXUS"
    LiXiang = "LIXIANG"
    Man = "MAN"
    MAZ = "MAZ"
    Mazda = "MAZDA"
    Mercedes_Benz = "MERCEDES_BENZ"
    Mitsubishi = "MITSUBISHI"
    Nissan = "NISSAN"
    Omoda = "OMODA"
    Opel = "OPEL"
    Peugeot = "PEUGEOT"
    Renault = "RENAULT"
    Scania = "SCANIA"
    Skoda = "SKODA"
    Suzuki = "SUZUKI"
    Toyota = "TOYOTA"
    Volkswagen = "VOLKSWAGEN"
    Volvo = "VOLVO"
    Zeekr = "ZEEKR"


class ObjectType(str, Enum):
    """Vehicle object types supported by the VMS vehicle filter."""

    Buses = "bus"
    Cars = "car"
    Trucks = "truck"
    Vans = "van"
