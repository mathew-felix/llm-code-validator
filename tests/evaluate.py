import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph import validate_code


def evaluate():
    # Load test cases
    with open("validation_dataset/test_cases.json") as f:
        test_cases = json.load(f)
    
    true_positives = 0   # Agent found a real issue
    false_positives = 0  # Agent flagged something that was fine
    false_negatives = 0  # Agent missed a real issue
    total_issues = 0
    
    results = []
    
    for i, test in enumerate(test_cases):
        print(f"Running test {i+1}/{len(test_cases)}: {test['id']}")
        
        try:
            result = validate_code(test["code"])
            report = result.get("report", {})
            found_issues = report.get("issues", [])
            known_issues = test["known_issues"]
            
            total_issues += len(known_issues)
            
            # Check each known issue — did the agent find it?
            for known in known_issues:
                found = any(
                    issue["line_number"] == known["line"] and
                    issue["issue_type"] == known["type"]
                    for issue in found_issues
                )
                if found:
                    true_positives += 1
                else:
                    false_negatives += 1
            
            # Check for false positives (agent flagged something not in known_issues)
            for found in found_issues:
                is_real = any(
                    found["line_number"] == known["line"]
                    for known in known_issues
                )
                if not is_real:
                    false_positives += 1
            
            results.append({
                "id": test["id"],
                "expected": len(known_issues),
                "found": len(found_issues),
                "true_positives": sum(1 for k in known_issues if any(
                    f["line_number"] == k["line"] for f in found_issues
                ))
            })
        
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"id": test["id"], "error": str(e)})
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    print("\n" + "="*50)
    print("VALIDATION RESULTS")
    print("="*50)
    print(f"Total test cases:   {len(test_cases)}")
    print(f"Total known issues: {total_issues}")
    print(f"True positives:     {true_positives}")
    print(f"False positives:    {false_positives}")
    print(f"False negatives:    {false_negatives}")
    print(f"Precision:          {precision:.1%}")
    print(f"Recall (TPR):       {recall:.1%}")
    
    # Save results
    with open("validation_dataset/results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": len(test_cases),
                "precision": precision,
                "recall": recall,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            },
            "per_test": results
        }, f, indent=2)
    
    print("\nResults saved to validation_dataset/results.json")


if __name__ == "__main__":
    evaluate()
