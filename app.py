
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

app.secret_key = "digital-certificate-secret-key"


# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["digital_certificate_db"]

certificates_collection = db["certificates"]
queries_collection = db["certificate_queries"]

# -----------------------------
# Temporary Issuer Details
# -----------------------------
# Later these will come from
# the logged-in issuer's account.

ISSUER = {
    "name": "Dr. Rajesh Patel",
    "email": "rajesh.patel@abc.edu",
    "institute": "ABC Institute of Technology"
}

# -----------------------------
# Temporary Issuer Details
# -----------------------------
# Later these will come from
# the logged-in student's account.

STUDENT = {
    "name": "Rahul Sharma",
    "email": "rahul@example.com"
}


# -----------------------------
# Generate Certificate ID
# -----------------------------
def generate_certificate_id():

    current_year = datetime.now().year

    count = certificates_collection.count_documents({})

    certificate_number = count + 1

    return f"CERT-{current_year}-{certificate_number:04d}"


# -----------------------------
# Issuer Dashboard
# -----------------------------
@app.route("/")
def issuer_dashboard():

    certificates = list(
        certificates_collection.find().sort("created_at", -1)
    )

    return render_template(
        "issuer_dashboard.html",
        issuer=ISSUER,
        certificates=certificates
    )


# -----------------------------
# Create Certificate Page(Issuer Creates Certificates)
# -----------------------------
@app.route("/create-certificate", methods=["GET", "POST"])
def create_certificate():

    if request.method == "POST":

        student_name = request.form.get("student_name")
        student_email = request.form.get("student_email")
        mobile = request.form.get("mobile")
        achievement = request.form.get("achievement")
        competition_name = request.form.get("competition_name")

        certificate_id = generate_certificate_id()

        certificate = {
            "certificate_id": certificate_id,

            "student_name": student_name,
            "student_email": student_email,
            "mobile": mobile,

            "achievement": achievement,
            "competition_name": competition_name,

            "institute_name": ISSUER["institute"],
            "issuer_name": ISSUER["name"],
            "issuer_email": ISSUER["email"],

            "status": "VALID",

            "issue_date": datetime.now().strftime("%d %B %Y"),
            "created_at": datetime.now(),

        }

        certificates_collection.insert_one(certificate)

        return redirect(
            url_for(
                "certificate",
                certificate_id=certificate_id
            )
        )

    return render_template(
        "create_certificate.html",
        issuer=ISSUER
    )



# -----------------------------
# View Certificate(General certificate view)
# -----------------------------
@app.route("/certificate/<certificate_id>")
def certificate(certificate_id):

    certificate_data = certificates_collection.find_one(
        {
            "certificate_id": certificate_id
        }
    )

    if not certificate_data:
        return "Certificate not found", 404

    return render_template(
        "certificate.html",
        certificate=certificate_data
    )





# -----------------------------
# Student Dashboard
# -----------------------------

@app.route("/student")
def student_dashboard():

    # Check login
    if "student_email" not in session:
        return redirect(url_for("student_login"))


    student_email = session["student_email"]
    student_name = session["student_name"]


    # Get student's certificates
    certificates = list(
        certificates_collection.find({
            "student_email": student_email
        }).sort("created_at", -1)
    )


    # Attach latest query to each certificate
    for certificate in certificates:

        latest_query = queries_collection.find_one(
            {
                "certificate_id":
                    certificate["certificate_id"],

                "student_email":
                    student_email
            },
            sort=[("created_at", -1)]
        )

        certificate["query"] = latest_query


    student = {
        "name": student_name,
        "email": student_email
    }


    return render_template(
        "student_dashboard.html",
        student=student,
        certificates=certificates
    )




# -----------------------------
# Student Views their own Certificate
# -----------------------------
@app.route("/student/certificate/<certificate_id>")
def student_certificate(certificate_id):

    # Check if student is logged in
    if "student_email" not in session:
        return redirect(url_for("student_login"))

    student_email = session["student_email"]

    student = {
        "name": session["student_name"],
        "email": session["student_email"]
    }

    certificate_data = certificates_collection.find_one({
        "certificate_id": certificate_id,
        "student_email": student_email
    })

    if not certificate_data:
        return "Certificate not found or access denied", 404

    return render_template(
        "student_certificate.html",
        student=student,
        certificate=certificate_data
    )




# -----------------------------
# Student Raise Query 
# -----------------------------

@app.route(
    "/student/certificate/<certificate_id>/query",
    methods=["GET", "POST"]
)
def raise_query(certificate_id):

    # Check student login
    if "student_email" not in session:
        return redirect(url_for("student_login"))

    student_email = session["student_email"]
    student_name = session["student_name"]

    # Find certificate belonging to logged-in student
    certificate_data = certificates_collection.find_one({
        "certificate_id": certificate_id,
        "student_email": student_email
    })

    if not certificate_data:
        return "Certificate not found or access denied", 404


    # Submit query
    if request.method == "POST":

        query_text = request.form.get("query_text")

        if not query_text or not query_text.strip():

            return render_template(
                "raise_query.html",
                student={
                    "name": student_name,
                    "email": student_email
                },
                certificate=certificate_data,
                error="Please describe the issue."
            )


        query = {

            "certificate_id": certificate_id,

            "student_name": student_name,
            "student_email": student_email,

            "query": query_text.strip(),

            "status": "PENDING",

            "response": None,

            "responded_by": None,

            "responded_at": None,

            "created_at": datetime.now()

        }


        queries_collection.insert_one(query)


        return redirect(
            url_for(
                "student_dashboard"
            )
        )


    return render_template(
        "raise_query.html",

        student={
            "name": student_name,
            "email": student_email
        },

        certificate=certificate_data
    )


# -----------------------------
# Student Login 
# -----------------------------

@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        student_name = request.form.get("student_name")
        student_email = request.form.get("student_email")

        # Find certificates belonging to this student
        certificates = list(
            certificates_collection.find({
                "student_email": student_email
            }).sort("created_at", -1)
        )

        # No certificate found
        if not certificates:

            return render_template(
                "student_login.html",
                error="No certificates found for this email."
            )

        # Store logged-in student in session
        session["student_name"] = student_name
        session["student_email"] = student_email

        return redirect(
            url_for("student_dashboard")
        )

    return render_template("student_login.html")


# -----------------------------
# Issuer Query page
# -----------------------------

@app.route("/issuer/queries")
def issuer_queries():

    queries = list(
        queries_collection.find().sort("created_at", -1)
    )

    return render_template(
        "issuer_queries.html",
        issuer=ISSUER,
        queries=queries
    )


# -----------------------------
# Route for the issuer to view one Query
# -----------------------------
@app.route("/issuer/query/<query_id>")
def issuer_query(query_id):

    from bson.objectid import ObjectId

    query_data = queries_collection.find_one({
        "_id": ObjectId(query_id)
    })

    if not query_data:
        return "Query not found", 404

    return render_template(
        "issuer_query.html",
        issuer=ISSUER,
        query=query_data
    )

# -----------------------------
# For updating the MongoDB Document, when issuer submits the response
# -----------------------------

@app.route(
    "/issuer/query/<query_id>/respond",
    methods=["POST"]
)
def respond_to_query(query_id):

    from bson.objectid import ObjectId

    response = request.form.get("response")
    status = request.form.get("status")

    queries_collection.update_one(
        {
            "_id": ObjectId(query_id)
        },
        {
            "$set": {
                "response": response,
                "status": status,
                "responded_by": ISSUER["name"],
                "responded_at": datetime.now()
            }
        }
    )

    return redirect(
        url_for(
            "issuer_query",
            query_id=query_id
        )
    )


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)