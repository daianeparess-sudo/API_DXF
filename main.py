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
        
        # Tenta descodificar de forma inteligente para lidar com o formato enviado pelo Bubble
        doc = None
        last_error = None

        # Tentativa 1: Leitura direta em bytes
        try:
            doc = ezdxf.read(io.BytesIO(file_content))
        except Exception as e1:
            last_error = str(e1)

        # Tentativa 2: Tratando como texto utf-8 (caso o Bubble envie string pura)
        if doc is None:
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
                doc = ezdxf.read(io.StringIO(text_content))
            except Exception as e2:
                last_error = f"Bytes: {last_error} | Text: {str(e2)}"

        # Tentativa 3: Tratando como latin-1 (para carateres especiais ou acentuação)
        if doc is None:
            try:
                text_content = file_content.decode('latin-1', errors='ignore')
                doc = ezdxf.read(io.StringIO(text_content))
            except Exception as e3:
                return jsonify({'error': f'Falha ao ler DXF: {last_error} | Latin1: {str(e3)}'}), 400

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