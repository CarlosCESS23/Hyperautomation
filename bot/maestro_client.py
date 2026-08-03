"""Cliente centralizado do BotCity Maestro."""

from botcity.maestro import BotMaestroSDK

from botcity.maestro import BotMaestroSDK


def criar_cliente() -> BotMaestroSDK:
    maestro = BotMaestroSDK.from_sys_args()

    if not maestro.is_online:
        raise ConnectionError("Não foi possível conectar ao BotCity Maestro.")

    return maestro