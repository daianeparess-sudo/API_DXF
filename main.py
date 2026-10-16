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

        # Utiliza o stream binário nativo do Flask/Werkzeug
        file_stream = file.stream
        
        doc = None
        erro_detalhado = ""

        # Tentativa 1: Ler diretamente os bytes do stream do ficheiro
        try:
            file_stream.seek(0)
            doc = ezdxf.read(file_stream)
        except Exception as e1:
            erro_detalhado += f" [Stream: {str(e1)}] "

        # Tentativa 2: Ler com file.read() tradicional encapsulado em BytesIO
        if doc is None:
            try:
                file.stream.seek(0)
                raw_bytes = file.read()
                doc = ezdxf.read(io.BytesIO(raw_bytes))
            except Exception as e2:
                erro_detalhado += f" [BytesIO: {str(e2)}] "

        # Tentativa 3: Caso venha como texto puro/string
        if doc is None:
            try:
                file.stream.seek(0)
                raw_bytes = file.read()
                text_content = raw_bytes.decode('utf-8', errors='ignore')
                doc = ezdxf.read(io.StringIO(text_content))
            except Exception as e3:
                erro_detalhado += f" [StringIO: {str(e3)}] "

        if doc is None:
            return jsonify({'error': f'Impossível ler DXF. Detalhes: {erro_detalhado}'}), 400

        msp = doc.modelspace()

        # Renderização da vista planificada para SVG utilizando o matplotlib
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