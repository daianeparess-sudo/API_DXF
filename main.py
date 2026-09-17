import os
import tempfile
from fastapi import FastAPI, File, HTTPException, UploadFile
import ezdxf

app = FastAPI()

@app.post("/calcular")
async def calcular_comprimento(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".dxf"):
        raise HTTPException(status_code=400, detail="Por favor, envie um arquivo .dxf")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            total_length = 0.0
            
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    length = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5
                    total_length += length
                elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    total_length += entity.length()
            
            return {
                "filename": file.filename,
                "total_length": round(total_length, 2),
                "unit": "unidades"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))