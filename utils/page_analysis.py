import os
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plt


def analyze_page_structure(url: str, output_dir: str = "analytics"):
    """
    Analyze a webpage's content distribution by HTML tag and save a bar chart.

    Args:
        url (str): The URL of the webpage to analyze.
        output_dir (str): Directory where analytics graphs will be saved.
    """

    # Ensure analytics directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Fetch the page
    response = requests.get(url)
    response.raise_for_status()
    html = response.text

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Count tag frequencies by text length
    tag_counts = {}
    for tag in soup.find_all(True):  # True = all tags
        tag_name = tag.name
        text_len = len(tag.get_text(strip=True))  # length of text inside tag
        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + text_len

    # Total text length
    total_len = sum(tag_counts.values())

    # Convert to percentages
    tag_percentages = {
        tag: (count / total_len) * 100 for tag, count in tag_counts.items() if total_len > 0
    }

    # Sort by contribution
    sorted_tags = dict(sorted(tag_percentages.items(), key=lambda x: x[1], reverse=True))

    # Plot as bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(sorted_tags.keys(), sorted_tags.values())
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Percentage of text content (%)")
    plt.title(f"Page Content Distribution by HTML Tag\n{url}")
    plt.tight_layout()

    # Save the figure
    safe_filename = url.replace("http://", "").replace("https://", "").replace("/", "_")
    filepath = os.path.join(output_dir, f"{safe_filename}_structure.png")
    plt.savefig(filepath, dpi=150)
    plt.close()

    return {
        "url": url,
        "output_file": filepath,
        "distribution": sorted_tags
    }


# Example usage:
if __name__ == "__main__":
    result = analyze_page_structure("https://www.espn.com/nba/schedule")
    print(f"Graph saved to: {result['output_file']}")
    print("Tag distribution (%):")
    for tag, pct in result["distribution"].items():
        print(f"{tag}: {pct:.2f}%")
