#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    pwd
)"

DIST_DIR="${PROJECT_ROOT}/dist/maestro"
BUILD_TEMP="$(mktemp -d)"

limpar_temporarios() {
    rm -rf -- "${BUILD_TEMP}"
}

trap limpar_temporarios EXIT

mkdir -p "${DIST_DIR}"

montar_pacote() {
    local bot_id="$1"
    local entrada="$2"
    local incluir_planilha="${3:-false}"

    local pacote_dir="${BUILD_TEMP}/${bot_id}"
    local arquivo_zip="${DIST_DIR}/${bot_id}.zip"

    mkdir -p "${pacote_dir}"

    cp -R \
        "${PROJECT_ROOT}/src" \
        "${pacote_dir}/src"

    cp \
        "${PROJECT_ROOT}/gerar_relatorio.py" \
        "${pacote_dir}/gerar_relatorio.py"

    cp \
        "${PROJECT_ROOT}/requirements.txt" \
        "${pacote_dir}/requirements.txt"

    cp \
        "${PROJECT_ROOT}/${entrada}" \
        "${pacote_dir}/bot.py"

    if [[ "${incluir_planilha}" == "true" ]]; then
        local planilha_demo="${PROJECT_ROOT}/data/input/inspecao_lotes_10dias.xlsx"

        if [[ -f "${planilha_demo}" ]]; then
            mkdir -p \
                "${pacote_dir}/data/input"

            cp \
                "${planilha_demo}" \
                "${pacote_dir}/data/input/inspecao_lotes_10dias.xlsx"
        else
            echo "Aviso: planilha de demonstração não encontrada."
            echo "O Bot A precisará receber um caminho válido no Runner."
        fi
    fi

    rm -f -- "${arquivo_zip}"

    (
        cd "${pacote_dir}"

        zip -qr \
            "${arquivo_zip}" \
            . \
            -x '*.pyc' \
            -x '*/__pycache__/*' \
            -x '.env' \
            -x '.env.*'
    )

    echo "Pacote criado: ${arquivo_zip}"
}

montar_pacote \
    "carlos_souza-entrada-v1" \
    "deploy/maestro/bot_a/bot.py" \
    "true"

montar_pacote \
    "carlos_souza-conferencia-v1" \
    "deploy/maestro/bot_b/bot.py"

montar_pacote \
    "carlos_souza-relatorio-v1" \
    "deploy/maestro/bot_c/bot.py"

echo
echo "Build dos três bots concluído."