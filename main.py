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
        
        doc = None
        erro_detalhado = ""

        # Tentativa 1: Leitura direta se forem bytes válidos
        try:
            doc = ezdxf.read(io.BytesIO(file_content))
        except Exception as e1:
            erro_detalhado += f" [B1: {str(e1)}] "

        # Tentativa 2: Decodificação Base64 (caso o Bubble envie o ficheiro codificado)
        if doc is None:
            try:
                decoded_bytes = base64.b64decode(file_content)
                doc = ezdxf.read(io.BytesIO(decoded_bytes))
            except Exception as e2:
                erro_detalhado += f" [B64: {str(e2)}] "

        # Tentativa 3: Conversão para texto limpo (UTF-8 / Latin-1)
        if doc is None:
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text_content = file_content.decode(encoding, errors='ignore')
                    # Limpa eventuais quebras de linha corrompidas pelo transporte HTTP
                    doc = ezdxf.read(io.StringIO(text_content))
                    break
                except Exception as e3:
                    erro_detalhado += f" [{encoding}: {str(e3)}] "

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