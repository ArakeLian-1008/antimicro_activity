import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
import psycopg2
import re
import requests
from rdkit import Chem
from PyPDF2 import PdfReader
import requests
from rdkit.Chem import Descriptors
from rdkit.Chem import rdMolDescriptors
import html



PORT = 8000

html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Canonize SMILES</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #E6FFE6;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: black;
        }}
        h1 {{
            color: #333;
        }}
        form {{
            margin-bottom: 30px;
            text-align: left;
        }}
        label {{
            display: block;
            margin-top: 10px;
        }}
        input[type="text"], input[type="number"], select {{
            width: 650px;
            padding: 10px;
            margin-top: 5px;
        }}
        button {{
            margin-top: 10px;
            padding: 10px 20px; /* Increased padding for a bigger button */
            font-size: 16px;    /* Increased font size for better visibility */
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 25px; /* Makes the button pill-shaped */
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            cursor: pointer;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .result {{
            margin-top: 20px;
            text-align: left;
        }}
        .error {{
            color: red;
        }}
        .bold {{
            font-weight: bold;
        }}
        .green {{
            color: green;
        }}

        /* Modal styles */
        .modal {{
            display: none; 
            position: fixed; 
            z-index: 1000; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            overflow: auto; 
            background-color: rgb(0,0,0); 
            background-color: rgba(0,0,0,0.5); 
            padding-top: 60px;
            font-family: Arial, sans-serif;
        }}

        .modal-content {{
            background-color: #fff;
            margin: 10% auto;
            padding: 20px;
            border-radius: 10px;
            width: 90%; 
            max-width: 700px;
            height: auto;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        }}

        .modal-content label {{
            font-weight: bold;
        }}

        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }}

        .close:hover,
        .close:focus {{
            color: black;
            text-decoration: none;
            cursor: pointer;
        }}
    </style>
    <script>
        function submitForm(action) {{
            document.getElementById('action').value = action;
            document.getElementById('smilesForm').submit();
        }}

        function showModal() {{
            document.getElementById('myModal').style.display = "block";
        }}

        function closeModal() {{
            document.getElementById('myModal').style.display = "none";
        }}

        window.onclick = function(event) {{
            if (event.target == document.getElementById('myModal')) {{
                closeModal();
            }}
        }}
    
        // Close modal on Escape key press
        document.addEventListener("keydown", function(event) {{
            if (event.key === "Escape") {{
                closeModal();
            }}
        }});

        function validateDOI() {{
            const doiInput = document.getElementById("doi");
            const doiError = document.getElementById("doiError");
            const regex = /^(10\.\d{{4,9}}\/[-._;()/:A-Za-z0-9]+)$/i; // Improved regex

            if (!regex.test(doiInput.value.trim()) && doiInput.value.trim() !== "") {{
                doiError.style.display = "block";
            }} else {{
                doiError.style.display = "none";
            }}
        }}

    </script>
</head>
<body>
    <div style="text-align: center;">
        <h1>Find matches and fullfill</h1>
        <form id="smilesForm" method="post" action="/">
            <label for="smiles"></label>
            <input
                type="text"
                id="smiles"
                name="smiles"
                placeholder="Enter SMILES or CAS"
                value="{smiles}"
            />
            <input type="hidden" id="action" name="action" value="match" />
            <button type="button" onclick="submitForm('match')">Match</button>
        </form>
        <div class="result">
            {result}
        </div>

    <!-- The Modal -->
    <div id="myModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <form method="post" action="/">
                {modal_inputs}
                <input type="hidden" name="smiles" value="{smiles}">
                <input type="hidden" name="action" value="insert">

                    <label for="activity">Activity:</label>
                    <select id="activity" name="activity" required>
                        <option value="mic">MIC</option>
                        <option value="mbc">MBC</option>
                        <option value="mbec">MBEC</option>
                        <option value="inhibition_zone">Inhibition Zone</option>
                        <option value="ec50">EC50</option>
                    </select><br><br>
 

                    <label for="value">Value:</label>
                    <input type="number" step="any" id="value" name="value" required><br><br>                  

                    <label for="statistics">Statistics (e.g., 0.54 (CI)):</label>
                    <input type="text" id="statistics" name="statistics" placeholder="Enter numeric value with text"><br><br>                   

                <!-- Incubation Input with Datalist -->
                <div>
                    <label for="incubation">Incubation:</label>
                    <input list="incubations" id="incubation" name="incubation" value="{selected_incubation}">
                    <datalist id="incubations">
                        {incubation_options}
                    </datalist>
                </div>

                <!-- Strain Input with Datalist -->
                <div>
                    <label for="strain">Strain:</label>
                    <input list="strains" id="strain" name="strain" value="{selected_strain}">
                    <datalist id="strains">
                        {strain_options}
                    </datalist>
                </div>   

                <!-- Incubation Input with Datalist -->
                <div>
                    <label for="taxon">TaxID:</label>
                    <input list="taxons" id="taxon" name="taxon" value="{selected_taxon}">
                    <datalist id="taxons">
                        {taxon_options}
                    </datalist>
                </div>                            

                <!-- Method Input with Datalist -->
                <div>
                    <label for="method">Method:</label>
                    <input list="methods" id="method" name="method" value="{selected_method}">
                    <datalist id="methods">
                        {method_options}
                    </datalist>
                </div>

                <!-- DOI -->
                    <label for="doi">DOI:</label>
                    <input type="text" id="doi" name="doi" value="" oninput="validateDOI()" required>
                    <span id="doiError" class="error" style="display: none; color: red; font-size: 0.9em;">Invalid DOI format. Format should be 10.xxxx/xxxx.</span>

                <!-- Notes -->
                <div class="form-group">
                    <label for="notes">Notes:</label>
                    <input type="text" id="notes" name="notes" value="">
                </div> 

                <!-- Created_by Input with Datalist -->
                <div>
                    <label for="created_by">Created_by:</label>
                    <select id="created_by" name="created_by" required>
                        <option value="" disabled selected>Select an annotator</option>
                        <option value="Alexander">Alexander</option>
                        <option value="Alexey">Alexey</option>
                        <option value="Andrey">Andrey</option>
                        <option value="Ulyana">Ulyana</option>
                    </select>
                </div>                             

                <!-- Submit Button -->
                <div class="form-group">
                    <button type="submit">Insert</button>
                </div>
            </form>
        </div>
    </div>

</body>
</html>
'''

# PostgreSQL connection parameters
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "susanna5691"
DB_HOST = "localhost"
DB_PORT = "5432"

def canonize_smiles(smiles):
    try:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule:
            return Chem.MolToSmiles(molecule, canonical=True)
        else:
            return "Invalid SMILES string"
    except Exception as e:
        return f"RDKit Error: {str(e)}"

# Extract metadata from DOI
def extract_doi_metadata(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            first_author = data['message']['author'][0]['family']
            # Try to extract the year from both 'published-print' and 'issued' fields
            year = None
            published_print = data['message'].get('published-print', {})
            if published_print.get('date-parts'):
                year = published_print['date-parts'][0][0]
            
            if not year:
                issued = data['message'].get('issued', {})
                if issued.get('date-parts'):
                    year = issued['date-parts'][0][0]
            journal = html.unescape(data['message']['container-title'][0])
            return f"{first_author}, {year}, {journal}"
        else:
            print(f"Error: DOI not found or API returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"Error extracting metadata from DOI: {e}")
        return None

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_template.format(smiles="", result="", modal_inputs="", method_options="", selected_method="", incubation_options="", selected_incubation="", strain_options="", selected_strain="", taxon_options="", selected_taxon="").encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(post_data.decode('utf-8'))
        smiles = params.get('smiles', [""])[0]
        action = params.get('action', [""])[0]      

        if action == 'insert':
            name = params.get('name', [""])[0]
            empirical_formula = params.get('empirical_formula', [""])[0]
            molecular_weight = params.get('molecular_weight', [""])[0]
            cas_number = params.get('cas_number', [""])[0]
            activity = params.get('activity', [""])[0]
            value = params.get('value', [""])[0]
            statistics = params.get('statistics', [""])[0]  
            incubation= params.get('incubation', [""])[0]
            strain = params.get('strain', [""])[0]
            taxon =  params.get('taxon', [""])[0]
            method = params.get('method', [""])[0]                               
            doi = params.get('doi', [""])[0]
            notes = params.get('notes', [""])[0]
            created_by = params.get('created_by', [""])[0]              
            data = {
                'smiles': smiles,
                'name': name,
                'empirical_formula': empirical_formula,             
                'molecular_weight': molecular_weight,
                'cas_number': cas_number,
                'activity': activity, 
                'value': value,                               
                'statistics': statistics,
                'incubation': incubation,
                'strain': strain,
                'taxon': taxon,                              
                'method': method,                               
                'doi': doi,
                'notes': notes,
                'created_by': created_by
                
            }
            is_valid, error_message = self.validate_data(data)
            if is_valid:
                self.insert_into_db(smiles, name, empirical_formula, molecular_weight, cas_number, activity, value, statistics, incubation, strain, taxon, method, doi, notes, created_by)
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html_template.format(smiles=smiles, result=f'<p class="error">{error_message}</p>', modal_inputs="", method_options="", selected_method=method, selected_incubation=incubation, incubation_options="", strain_options="", selected_strain=strain, taxon_options="", selected_taxon=taxon).encode())
        else:
            self.find_matches_and_respond(smiles)

    def validate_data(self, data):
        required_fields = ['strain']
        for field in required_fields:
            if not data.get(field):
                return False, f"The field {field} is required."
        return True, ""

    

    def insert_into_db(self, smiles, name, empirical_formula, molecular_weight, cas_number, activity, value, statistics, incubation, strain, taxon, method, doi, notes, created_by):
        canonical_smiles = canonize_smiles(smiles)

        # Extract metadata from DOI
        reference = extract_doi_metadata(doi) if doi else None

        # Strip whitespace from inputs
        smiles = smiles.strip()
        name = name.strip()
        cas_number = cas_number.strip()
        strain = strain.strip()
        method = method.strip()
        statistics = statistics.strip()

        # Insert into PostgreSQL
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user="postgres",
                password="susanna5691",
                host="localhost",
                port=5432
            )
            cursor = conn.cursor()
            
            column_name = activity

            insert_query = f"""
            INSERT INTO template (smiles, name, empirical_formula, molecular_weight, cas, {column_name}, {column_name}_statistics, incubation, strain, taxon, method, reference, doi, notes, created_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)    
            """
            cursor.execute(insert_query, (canonical_smiles, name, empirical_formula, molecular_weight, cas_number, value, statistics, incubation, strain, None if taxon==""  else int(taxon), method,  reference, doi, notes, created_by))
            conn.commit()

            result = f'''
            <p class="green"><span class="bold">Name :</span> {name}</p>
            <p class="green"><span class="bold">Empirical Formula :</span> {empirical_formula}</p>
            <p class="green"><span class="bold">CAS Number :</span> {cas_number}</p>
            <p class="green"><span class="bold">SMILES :</span> {canonical_smiles}</p>  
            <p class="green"><span class="bold">Molecular Weight :</span> {molecular_weight}</p>                      
            <p class="green"><span class="bold">Activity :</span> {activity}</p> 
            <p class="green"><span class="bold">Value :</span> {value}</p>             
            <p class="green"><span class="bold">Statistics :</span> {statistics}</p>   
            <p class="green"><span class="bold">Incubation :</span> {incubation}</p> 
            <p class="green"><span class="bold">Strain :</span> {strain}</p>
            <p class="green"><span class="bold">TaxID :</span> {taxon}</p>                                    
            <p class="green"><span class="bold">Method :</span> {method}</p>   
            <p class="green"><span class="bold">Reference :</span> {reference}</p>                                    
            <p class="green"><span class="bold">DOI :</span> {doi}</p>
            <p class="green"><span class="bold">Notes :</span> {notes}</p>
            <p class="green"><span class="bold">Created By :</span> {created_by}</p>              
            <p class="green">Data successfully inserted into database.</p>
            '''
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            result = f'<p class="error">Error inserting into database: {str(e)}</p>'
        
        # Respond to client
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_template.format(smiles=smiles, result=result, modal_inputs="", method_options="", selected_method=method, selected_incubation=incubation, incubation_options="", strain_options="", selected_strain=strain, taxon_options="", selected_taxon=taxon).encode())

    def find_matches_and_respond(self, smiles):
        canonical_smiles = canonize_smiles(smiles)
        cas_number = smiles.strip()

        print (smiles)
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user="postgres",
                password="susanna5691",
                host="localhost",
                port="5432"
            )
            cursor = conn.cursor()

            # Query for matches using SMILES
            cursor.execute("SELECT DISTINCT name, empirical_formula, molecular_weight, cas FROM test WHERE smiles = %s", (canonical_smiles,))
            test_smiles_rows = cursor.fetchall()
            cursor.execute("SELECT DISTINCT name, empirical_formula, molecular_weight, cas FROM template WHERE smiles = %s", (canonical_smiles,))
            template_smiles_rows = cursor.fetchall()

            # Query for matches using CAS number
            cursor.execute("SELECT DISTINCT name, empirical_formula, molecular_weight, cas FROM test WHERE cas = %s", (cas_number,))
            test_cas_rows = cursor.fetchall()
            cursor.execute("SELECT DISTINCT name, empirical_formula, molecular_weight, cas FROM template WHERE cas = %s", (cas_number,))
            template_cas_rows = cursor.fetchall()

            # Combine results from both SMILES and CAS number queries
            rows = list(set(test_smiles_rows + template_smiles_rows + test_cas_rows + template_cas_rows))

            # Check if there are matches
            if rows:
                match_info = rows[0]  # Use the first match
                name = match_info[0] if match_info[0] else ""
                empirical_formula = match_info[1] if match_info[1] else ""
                molecular_weight = f"{float(match_info[2]):.2f}" if match_info[2] else ""
                cas_number = match_info[3] if match_info[3] else ""


                modal_inputs = f'''
                    <div>
                        <label>Name:</label>
                        <span>{name}</span>
                        <input type="hidden" id="name" name="name" value="{name}">
                    </div>
                    <div>
                        <label>Empirical Formula:</label>
                        <span>{empirical_formula}</span>
                        <input type="hidden" id="empirical_formula" name="empirical_formula" value="{empirical_formula}">
                    </div>
                    <div>
                        <label>CAS Number:</label>
                        <span>{cas_number}</span>
                        <input type="hidden" id="cas_number" name="cas_number" value="{cas_number}">
                    </div>
                    <div>
                        <label>Molecular Weight:</label>
                        <span>{molecular_weight}</span>
                        <input type="hidden" id="molecular_weight" name="molecular_weight" value="{molecular_weight}">
                    </div>
                '''
            else:
                # No match found, use RDKit to calculate empirical formula and molecular weight
                molecule = Chem.MolFromSmiles(canonical_smiles)
                if molecule:
                    empirical_formula = rdMolDescriptors.CalcMolFormula(molecule)
                    molecular_weight = f"{Descriptors.MolWt(molecule):.2f}"
                else:
                    empirical_formula = ""
                    molecular_weight = ""

                modal_inputs = f'''
                    <div>
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" value="">
                    </div>
                    <div>
                        <label>Empirical Formula:</label>
                        <span>{empirical_formula}</span>
                        <input type="hidden" id="empirical_formula" name="empirical_formula" value="{empirical_formula}">
                    </div>
                    <div>
                        <label for="cas_number">CAS Number:</label>
                        <input type="text" id="cas_number" name="cas_number" value="">
                    </div>
                    <div>
                        <label>Molecular Weight:</label>
                        <span>{molecular_weight}</span>
                        <input type="hidden" id="molecular_weight" name="molecular_weight" value="{molecular_weight}">
                    </div>
                '''


            # Get distinct incubations from the database
            cursor.execute("SELECT DISTINCT incubation FROM template ORDER BY incubation ASC;")
            incubations = cursor.fetchall()
            incubation_options = ''.join([f'<option value="{incubation[0]}">{incubation[0]}</option>' for incubation in incubations]) 

            # Get distinct strains from the database
            cursor.execute("SELECT DISTINCT strain FROM template")
            strains = cursor.fetchall()
            strain_options = ''.join([f'<option value="{strain[0]}">{strain[0]}</option>' for strain in strains])

            # Get distinct taxons from the database
            cursor.execute("SELECT DISTINCT taxon FROM template ORDER BY taxon ASC;")
            taxons = cursor.fetchall()
            taxon_options = ''.join([f'<option value="{taxon[0]}">{taxon[0]}</option>' for taxon in taxons]) 

            # Get distinct methods from the database
            cursor.execute("SELECT DISTINCT method FROM template")
            methods = cursor.fetchall()
            method_options = ''.join([f'<option value="{method[0]}">{method[0]}</option>' for method in methods])
            
            
            if rows:
                result = '''
                <p class="green">Matches found. Please review and confirm the details:{smiles}</p>
                <button type="button" onclick="showModal()">Review Details</button>
                '''
                if smiles.strip().replace("-", "").isnumeric():
                    result = f'''
                        <p class="green">Matches found. Please review and confirm the details:</p>
                        <button type="button" onclick="showModal()">Review Details</button>
                    '''
                else:
                    result = f'''
                        <p class="green">Matches found. Please review and confirm the details:</p>
                        <button type="button" onclick="showModal()">Review Details</button>
                    '''
            else:
                if smiles.strip().replace("-", "").isnumeric():
                    result = f'''
                        <p class="error">No matches found. Please enter the SMILES:</p>
                    '''
                else:
                    result = f'''
                        <p class="error">No matches found. Please enter the details manually:</p>
                        <button type="button" onclick="showModal()">Enter Details</button>
                    '''
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            modal_inputs = ''
            incubation_options = ''            
            strain_options = ''
            taxon_options = ''
            method_options = ''
            result = f'<p class="error">Error accessing database: {str(e)}</p>'
        
        # Respond to client
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_template.format(smiles=smiles, result=result, modal_inputs=modal_inputs, method_options=method_options, selected_method="", incubation_options=incubation_options, selected_incubation="", strain_options=strain_options, selected_strain="", taxon_options=taxon_options, selected_taxon="").encode())

def start_server():
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at port {PORT}")
        webbrowser.open(f'http://localhost:{PORT}')
        httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    input("Press Enter to stop the server...\n")
