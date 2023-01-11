#-------------------------------------------------------------------------------
# es7s [setup/configuration/commons]
# (c) 2021-2023 A. Shavykin <0.delameter@gmail.com>
#-------------------------------------------------------------------------------

PROJECT_NAME="${1:?Project name required}"
DEPENDS_PATH="${2:?Output path required}"

venv/bin/pydeps ${PROJECT_NAME} \
    --rmprefix ${PROJECT_NAME}. \
    --start-color 120 \
    --only ${PROJECT_NAME} \
    -o ${DEPENDS_PATH}/structure.svg

venv/bin/pydeps ${PROJECT_NAME} \
    --rmprefix ${PROJECT_NAME}. \
    --start-color 120 \
    --show-cycle \
    -o ${DEPENDS_PATH}/cycles.svg

venv/bin/pydeps ${PROJECT_NAME} \
    --start-color 0 \
    --max-bacon 3 \
    --max-mod 0 \
    --max-cluster 100 \
    --keep \
    -o ${DEPENDS_PATH}/imports-deep.svg

venv/bin/pydeps ${PROJECT_NAME} \
    --start-color 0 \
    --max-bacon 3 \
    --cluster \
    --collapse \
    -o ${DEPENDS_PATH}/imports-cross.svg

venv/bin/pydeps ${PROJECT_NAME} \
    --start-color 0 \
    --max-bacon 12 \
    --max-mod 1 \
    --cluster \
    --collapse \
    -o ${DEPENDS_PATH}/imports-far.svg
