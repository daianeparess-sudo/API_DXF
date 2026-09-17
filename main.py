import os
import subprocess
import tempfile
from fastapi import FastAPI, File, HTTPException, UploadFile
import ezdxf

app = FastAPI()


def convert_dwg_to_dxf(dwg_path: str, output_dir: str) -> str:
  """Converte um arquivo DWG para DXF usando o ODAFileConverter instalado no sistema."""
  dxf_path = os.path.join(
      output_dir, os.path.splitext(os.path.basename(dwg_path))[0] + ".dxf"
  )

  # ODAFileConverter aceita a pasta de entrada e a pasta de saída como argumentos
  # Sintaxe: ODAFileConverter <input_dir> <output_dir> <output_version> <output_type> <recurse>
  cmd = [
      "ODAFileConverter",
      os.path.dirname(dwg_path),
      output_dir,
      "ACAD2018",
      "DXF",
      "0",
  ]

  try:
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
    )
    if not os.path.exists(dxf_path):
      raise Exception(
          f"Erro na conversão ODA: {result.stdout} {result.stderr}"
      )
    return dxf_path
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Falha ao converter arquivo DWG: {str(e)}"
    )


@app.post("/calcular")
async def calcular_comprimento(file: UploadFile = File(...)):
  filename = file.filename.lower()
  if not (filename.endswith(".dxf") or filename.endswith(".dwg")):
    raise HTTPException(
        status_code=400,
        detail="Formato inválido. Envie um arquivo .dxf ou .dwg",
    )

  # Cria um diretório temporário seguro para processar os arquivos
  with tempfile.TemporaryDirectory() as temp_dir:
    input_file_path = os.path.join(temp_dir, file.filename)

    # Salva o arquivo enviado pelo Bubble no disco temporário
    contents = await file.read()
    with open(input_file_path, "wb") as f:
      f.write(contents)

    target_dxf_path = input_file_path

    # Se for DWG, fazemos a conversão para DXF
    if filename.endswith(".dwg"):
      target_dxf_path = convert_dwg_to_dxf(input_file_path, temp_dir)

    # Processa o arquivo DXF com o ezdxf para somar o comprimento das linhas
    try:
      doc = ezdxf.readfile(target_dxf_path)
      msp = doc.modelspace()

      total_length = 0.0

      # Itera sobre todas as entidades de linha (LINE) e polilinhas (LWPOLYLINE / POLYLINE)
      for entity in msp:
        if entity.dxftype() == "LINE":
          start = entity.dxf.start
          end = entity.dxf.end
          length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
          total_length += length
        elif entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
          # Calcula o comprimento da polilinha
          total_length += entity.length()

      return {
          "filename": file.filename,
          "total_length": round(total_length, 2),
          "unit": "unidades do desenho",
      }

    except Exception as e:
      raise HTTPException(
          status_code=500, detail=f"Erro ao processar a geometria: {str(e)}"
      )