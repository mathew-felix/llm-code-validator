import httpx
from agent.schemas import AgentState
from agent.utils import is_likely_local_module

# Maps Python import names to their PyPI distribution names
# when they do not match directly.
IMPORT_TO_DISTRIBUTION = {
    "yaml": "PyYAML",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "bs4": "beautifulsoup4",
    "wx": "wxPython",
    "serial": "pyserial",
    "Crypto": "pycryptodome",
    "dotenv": "python-dotenv",
    "attr": "attrs",
    "dateutil": "python-dateutil",
    "jwt": "PyJWT",
    "magic": "python-magic",
    "pkg_resources": "setuptools",
    "gi": "PyGObject",
    "usb": "pyusb",
}


def fetch_pypi_node(state: dict) -> dict:
    """
    NODE 3 (Optional): Fetch package metadata from PyPI for unknown libraries.
    
    What it does: For every library NOT in our local database,
    hits the free PyPI JSON API to get current version info.
    
    Why this helps: Even without method signatures, knowing the
    current version lets the LLM reason about whether the code's
    imports are plausible.
    
    Important: This only runs if needs_pypi_fetch is True.
    The conditional router in the graph skips this node otherwise.
    """
    
    pypi_data = {}
    libraries_unknown = state.get("libraries_unknown", [])
    
    for library in libraries_unknown:
        if is_likely_local_module(library):
            continue

        try:
            # PyPI JSON API — completely free, no auth required
            pypi_name = IMPORT_TO_DISTRIBUTION.get(library, library)
            url = f"https://pypi.org/pypi/{pypi_name}/json"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                info = data["info"]
                
                pypi_data[library] = {
                    "found": True,
                    "latest_version": info["version"],
                    "summary": info["summary"],
                    "requires_python": info.get("requires_python", "unknown"),
                    "home_page": info.get("home_page", ""),
                    "distribution_name": pypi_name,
                    "note": "Library found on PyPI but not in local signature database. LLM reasoning quality may be lower."
                }
                print(f"PyPI: Found {library} as {pypi_name} v{info['version']}")
            
            elif response.status_code == 404:
                # Package doesn't exist on PyPI at all
                pypi_data[library] = {
                    "found": False,
                    "note": "Package not found on PyPI. This import may be hallucinated."
                }
                print(f"PyPI: {library} NOT FOUND — possible hallucination")
            
            else:
                pypi_data[library] = {
                    "found": None,
                    "note": f"PyPI returned status {response.status_code}"
                }
        
        except httpx.TimeoutException:
            pypi_data[library] = {
                "found": None,
                "note": "PyPI request timed out"
            }
        except Exception as e:
            pypi_data[library] = {
                "found": None,
                "note": f"Error fetching PyPI data: {str(e)}"
            }
    
    return {**state, "pypi_data": pypi_data}
