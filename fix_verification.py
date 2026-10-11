with open(r'D:\python\vs code\clg works\verification.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''startButton.addEventListener(
            "click",
            async function() {

                if (!fileInput.files ||
                    fileInput.files.length === 0
                ) {

                    alert(
                        "Please choose a document first."
                    );

                    return;
                }


                var file =
                    fileInput.files[0];


                var selectedType =
                    documentType.value;


                startButton.disabled =
                    true;


                processing
                    .classList
                    .add(
                        "show"
                    )


                resultContainer
                    .classList
                    .remove(
                        "show"
                    )


                fileStatus.textContent =
                    "Processing"


                processingText.textContent =
                    "Connecting to verification server..."


                try {


                    / ================================================
                       FORM DATA
                    ================================================= /

                    var formData =
                        new FormData()


                    formData.append(
                        "document_type",
                        selectedType
                    )


                    formData.append(
                        "file",
                        file
                    )


                    / ================================================
                       API REQUEST
                    ================================================= /

                    processingText.textContent =
                        "Running OCR and document verification..."


                    var response =
                        await fetch(
                            API_URL +
                            "/api/verify", {
                                method: "POST",

                                body: formData
                            }
                        )


                    / ================================================
                       READ RESPONSE
                    ================================================= /

                    var responseText =
                        await response.text()


                    var data


                    try {

                        data =
                            JSON.parse(
                                responseText
                            )

                    } catch (parseError) {

                        throw new Error(
                            "Backend returned an invalid response."
                        )
                    }


                    / ================================================
                       SERVER ERROR
                    ================================================= /

                    if (!response.ok) {

                        var message =
                            "HTTP " +
                            response.status


                        if (
                            typeof data.detail ===
                            "string"
                        ) {

                            message =
                                data.detail

                        } else if (
                            data.detail &&
                            data.detail.message
                        ) {

                            message =
                                data.detail.message

                        } else if (
                            data.message
                        ) {

                            message =
                                data.message
                        }


                        throw new Error(
                            message
                        )
                    }


                    / ================================================
                       APPLICATION ERROR
                    ================================================= /

                    if (
                        data.success !== true
                    ) {

                        throw new Error(
                            data.error ||
                            data.message ||
                            "Verification failed."
                        )
                    }


                    / ================================================
                       DISPLAY
                    ================================================= /

                    showResult(
                        data
                    )


                    fileStatus.textContent =
                        "Complete"


                    processingText.textContent =
                        "Verification completed."

                } catch (error) {

                    console.error(
                        "VERISHIELD ERROR:",
                        error
                    )


                    fileStatus.textContent =
                        "Error"


                    resultContainer
                        .classList
                        .add(
                            "show"
                        )


                    resultHeader.className =
                        "result-head danger"


                    resultStatus.textContent =
                        "VERIFICATION ERROR"


                    riskScore.textContent =
                        "-"

                    riskLevel.textContent =
                        "-"

                    validationScore.textContent =
                        "-"

                    ocrConfidence.textContent =
                        "-"

                    blacklistStatus.textContent =
                        "-"

                    tamperingScore.textContent =
                        "-"


                    displayFields({
                        error: error.message
                    })


                    processingText.textContent =
                        "Verification failed."


                    alert(
                        "Verification failed:\n\n" +
                        error.message
                    )

                } finally {

                    processing
                        .classList
                        .remove(
                            "show"
                        )


                    startButton.disabled =
                        false
                }
            }
        )'''

# The actual content in the file uses different comment format
# Let me find it with regex and replace
import re

# Find the exact event listener
pattern = r'(startButton\.addEventListener\([\s\S]*?}\);)'
match = re.search(pattern, content)
if match:
    old_exact = match.group(1)
    print("Found event listener, length:", len(old_exact))
    
    new = '''startButton.addEventListener(
            "click",
            async function() {

                if (!fileInput.files ||
                    fileInput.files.length === 0
                ) {

                    alert(
                        "Please choose a document first."
                    );

                    return;
                }


                var file =
                    fileInput.files[0];


                var selectedType =
                    documentType.value;


                startButton.disabled =
                    true;


                processing
                    .classList
                    .add(
                        "show"
                    )


                resultContainer
                    .classList
                    .remove(
                        "show"
                    )


                fileStatus.textContent =
                    "Processing"


                processingText.textContent =
                    "Connecting to verification server..."


                var controller = new AbortController();
                var timeoutId = setTimeout(function() {
                    controller.abort();
                }, REQUEST_TIMEOUT);

                try {


                    /* ================================================
                       FORM DATA
                    ================================================= */

                    var formData =
                        new FormData()


                    formData.append(
                        "document_type",
                        selectedType
                    )


                    formData.append(
                        "file",
                        file
                    )


                    /* ================================================
                       API REQUEST
                    ================================================= */

                    processingText.textContent =
                        "Uploading document..."

                    var response =
                        await fetch(
                            API_URL +
                            "/api/verify", {
                                method: "POST",
                                body: formData,
                                signal: controller.signal
                            }
                        )


                    clearTimeout(timeoutId)


                    /* ================================================
                       READ RESPONSE
                    ================================================= */

                    processingText.textContent =
                        "Running OCR and document verification (this may take 15-30s)..."

                    var responseText =
                        await response.text()


                    var data


                    try {

                        data =
                            JSON.parse(
                                responseText
                            )

                    } catch (parseError) {

                        throw new Error(
                            "Backend returned an invalid response."
                        )
                    }


                    /* ================================================
                       SERVER ERROR
                    ================================================= */

                    if (!response.ok) {

                        var message =
                            "HTTP " +
                            response.status


                        if (
                            typeof data.detail ===
                            "string"
                        ) {

                            message =
                                data.detail

                        } else if (
                            data.detail &&
                            data.detail.message
                        ) {

                            message =
                                data.detail.message

                        } else if (
                            data.message
                        ) {

                            message =
                                data.message
                        }


                        throw new Error(
                            message
                        )
                    }


                    /* ================================================
                       APPLICATION ERROR
                    ================================================= */

                    if (
                        data.success !== true
                    ) {

                        throw new Error(
                            data.error ||
                            data.message ||
                            "Verification failed."
                        )
                    }


                    /* ================================================
                       DISPLAY
                    ================================================= */

                    showResult(
                        data
                    )


                    fileStatus.textContent =
                        "Complete"


                    processingText.textContent =
                        "Verification completed."

                } catch (error) {

                    clearTimeout(timeoutId)

                    console.error(
                        "VERISHIELD ERROR:",
                        error
                    )


                    fileStatus.textContent =
                        "Error"


                    resultContainer
                        .classList
                        .add(
                            "show"
                        )


                    resultHeader.className =
                        "result-head danger"


                    resultStatus.textContent =
                        "VERIFICATION ERROR"


                    riskScore.textContent =
                        "-"

                    riskLevel.textContent =
                        "-"

                    validationScore.textContent =
                        "-"

                    ocrConfidence.textContent =
                        "-"

                    blacklistStatus.textContent =
                        "-"

                    tamperingScore.textContent =
                        "-"


                    displayFields({
                        error: error.message
                    })


                    processingText.textContent =
                        "Verification failed."

                    var errorMessage = error.message
                    if (error.name === "AbortError") {
                        errorMessage = "Request timed out (" + (REQUEST_TIMEOUT/1000) + "s). The document may be too complex or the server is overloaded. Try a clearer image or smaller file."
                    }

                    alert(
                        "Verification failed:\n\n" +
                        errorMessage
                    )

                } finally {

                    processing
                        .classList
                        .remove(
                            "show"
                        )


                    startButton.disabled =
                        false
                }
            }
        )'''

    content = content.replace(old_exact, new)
    with open(r'D:\python\vs code\clg works\verification.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Replaced event listener')
else:
    print('NOT FOUND')