import os
import io
import base64
from flask import Flask, request, jsonify
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/calcular-lote', methods=['POST'])
def calcular_lote():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado no parâmetro "file"'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome do arquivo vazio'}), 400

        file_content = file.read()
        
        # Tenta ler como bytes (padrão)
        try:
            doc = ezdxf.read(io.BytesIO(file_content))
        except Exception:
            # Se falhar, converte para texto e lê com io.StringIO usando ezdxf.read()
            text_content = file_content.decode('utf-8', errors='ignore')
            doc = ezdxf.read(io.StringIO(text_content))

        msp = doc.modelspace()

        # Renderiza a geometria planificada para SVG usando matplotlib
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        svg_io = io.BytesIO()
        fig.savefig(svg_io, format='svg', bbox_inches='tight')
        plt.close(fig)
        
        svg_io.seek(0)
        dxf_svg_content = svg_io.getvalue().decode('utf-8')

        response_data = {
            'dxf_svg': dxf_svg_content,
            'status': 'sucesso',
            'mensagem': 'DXF processado e planificado com sucesso'
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)