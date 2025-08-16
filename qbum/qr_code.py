import qrcode
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
import struct


def create_qr_code(
    url: str,
    back_color: str = "ffffff",
    front_color: str = "0a0a0a",
) -> StyledPilImage:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            back_color=struct.unpack("BBB", bytes.fromhex(back_color)),
            front_color=struct.unpack("BBB", bytes.fromhex(front_color)),
        ),
    )
    # https://stackoverflow.com/a/4296263/4737417
    return img


if __name__ == "__main__":
    img = create_qr_code(
        "https://pintergreg.github.io/quantifying-barriers-of-urban-mobility/"
    )
    img.save("static/images/qr_code.png")
