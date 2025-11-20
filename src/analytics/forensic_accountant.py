"""
Forensic Accountant Module - Financial Pattern Recognition

This module identifies suspicious financial activity using:
1. Benford's Law Test - Analyzes leading digits of payments
2. Round Number Anomaly - Flags high frequency of "clean" numbers
"""

import re
import csv
import sqlite3
from typing import List, Dict, Tuple
from collections import Counter
import numpy as np
from scipy import stats
from pathlib import Path

from .database import get_db_connection


class ForensicAccountant:
    """
    Analyzes financial patterns to detect anomalies.
    """
    
    def __init__(self, db_path: str = "data/epstein_analysis.db"):
        """
        Initialize the Forensic Accountant.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.amounts = []  # List of (amount, doc_id, doc_hash, page_number, filename, context)
        
        # Benford's Law expected distribution for leading digit
        self.benford_expected = {
            1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
            6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
        }
    
    def extract_currency_amounts(self, text: str) -> List[Tuple[float, str]]:
        """
        Extract currency amounts from text.
        
        Args:
            text: Document text
            
        Returns:
            List of (amount, context) tuples
        """
        amounts = []
        
        # Pattern for currency amounts: $X,XXX.XX or $X.XX or $X,XXX
        patterns = [
            r'\$\s*([\d,]+\.?\d*)',  # $1,234.56 or $1,234 or $1234.56
            r'USD\s*([\d,]+\.?\d*)',  # USD 1,234.56
            r'([\d,]+\.?\d*)\s*(?:dollars|USD)',  # 1,234.56 dollars
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    if amount > 0:  # Only positive amounts
                        # Get context (50 chars before and after)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].replace('\n', ' ')
                        amounts.append((amount, context))
                except ValueError:
                    continue
        
        return amounts
    
    def load_financial_data(self, limit: int = None) -> None:
        """
        Load financial data from documents.
        
        Args:
            limit: Optional limit on documents to process
        """
        print("Extracting currency amounts from documents...")
        
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get all documents
        if limit:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents")
        
        doc_count = 0
        amount_count = 0
        
        for row in cursor.fetchall():
            doc_id = row[0]
            filename = row[1]
            doc_hash = row[2]
            text = row[3]
            page_number = row[4]
            
            # Extract amounts from this document
            amounts = self.extract_currency_amounts(text)
            
            for amount, context in amounts:
                self.amounts.append((amount, doc_id, doc_hash, page_number, filename, context))
                amount_count += 1
            
            doc_count += 1
            if doc_count % 100 == 0:
                print(f"Processed {doc_count} documents, found {amount_count} amounts")
        
        conn.close()
        
        print(f"\nExtracted {amount_count} currency amounts from {doc_count} documents")
    
    def get_leading_digit(self, amount: float) -> int:
        """
        Get the leading digit of a number.
        
        Args:
            amount: Numerical amount
            
        Returns:
            Leading digit (1-9)
        """
        amount_str = f"{amount:.0f}"
        first_digit = int(amount_str[0])
        return first_digit if first_digit > 0 else None
    
    def benford_test(self) -> Dict:
        """
        Perform Benford's Law test on the extracted amounts.
        
        Returns:
            Dictionary with test results
        """
        print("\nPerforming Benford's Law test...")
        
        if not self.amounts:
            print("Warning: No amounts to analyze")
            return {}
        
        # Get leading digits
        leading_digits = []
        for amount, _, _, _, _, _ in self.amounts:
            digit = self.get_leading_digit(amount)
            if digit:
                leading_digits.append(digit)
        
        if not leading_digits:
            print("Warning: No valid leading digits found")
            return {}
        
        # Calculate observed frequencies
        digit_counts = Counter(leading_digits)
        total = len(leading_digits)
        
        observed = {}
        for digit in range(1, 10):
            observed[digit] = digit_counts.get(digit, 0) / total
        
        # Calculate chi-square statistic
        chi_square = 0
        deviations = {}
        
        for digit in range(1, 10):
            expected = self.benford_expected[digit]
            obs = observed[digit]
            deviation = (obs - expected) / expected if expected > 0 else 0
            deviations[digit] = deviation
            
            # Chi-square contribution
            chi_square += ((obs * total - expected * total) ** 2) / (expected * total)
        
        # Chi-square test (8 degrees of freedom for digits 1-9)
        p_value = 1 - stats.chi2.cdf(chi_square, df=8)
        
        # Flag if p-value < 0.05 (significant deviation from Benford's Law)
        is_suspicious = p_value < 0.05
        
        result = {
            'total_amounts': total,
            'observed_distribution': observed,
            'expected_distribution': self.benford_expected,
            'deviations': deviations,
            'chi_square': chi_square,
            'p_value': p_value,
            'is_suspicious': is_suspicious
        }
        
        print(f"  Total amounts analyzed: {total}")
        print(f"  Chi-square statistic: {chi_square:.4f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Suspicious: {'YES' if is_suspicious else 'NO'}")
        
        return result
    
    def round_number_analysis(self) -> Dict:
        """
        Analyze frequency of round numbers.
        
        Returns:
            Dictionary with analysis results
        """
        print("\nPerforming round number analysis...")
        
        if not self.amounts:
            print("Warning: No amounts to analyze")
            return {}
        
        total = len(self.amounts)
        round_count = 0
        very_round_count = 0
        round_amounts = []
        
        for amount, doc_id, doc_hash, page_number, filename, context in self.amounts:
            # Check if round (divisible by 1000)
            if amount >= 1000 and amount % 1000 == 0:
                round_count += 1
                round_amounts.append((amount, doc_id, doc_hash, page_number, filename, context))
                
                # Check if very round (divisible by 10000)
                if amount % 10000 == 0:
                    very_round_count += 1
        
        round_percentage = (round_count / total * 100) if total > 0 else 0
        very_round_percentage = (very_round_count / total * 100) if total > 0 else 0
        
        # Flag if more than 30% are round numbers (typical threshold)
        is_suspicious = round_percentage > 30
        
        result = {
            'total_amounts': total,
            'round_count': round_count,
            'very_round_count': very_round_count,
            'round_percentage': round_percentage,
            'very_round_percentage': very_round_percentage,
            'is_suspicious': is_suspicious,
            'round_amounts': round_amounts
        }
        
        print(f"  Total amounts: {total}")
        print(f"  Round numbers (÷1000): {round_count} ({round_percentage:.2f}%)")
        print(f"  Very round (÷10000): {very_round_count} ({very_round_percentage:.2f}%)")
        print(f"  Suspicious: {'YES' if is_suspicious else 'NO'}")
        
        return result
    
    def export_report(self, benford_result: Dict, round_result: Dict, 
                     output_path: str = "financial_analysis_report.csv") -> None:
        """
        Export financial analysis report with source citations.
        
        Args:
            benford_result: Results from Benford's Law test
            round_result: Results from round number analysis
            output_path: Path to output CSV file
        """
        print(f"\nExporting financial report to: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write summary
            writer.writerow(['FINANCIAL ANALYSIS SUMMARY'])
            writer.writerow([])
            writer.writerow(['Total Amounts Analyzed', benford_result.get('total_amounts', 0)])
            writer.writerow([])
            
            # Benford's Law results
            writer.writerow(['BENFORD\'S LAW TEST'])
            writer.writerow(['Chi-square', f"{benford_result.get('chi_square', 0):.4f}"])
            writer.writerow(['P-value', f"{benford_result.get('p_value', 0):.4f}"])
            writer.writerow(['Suspicious', 'YES' if benford_result.get('is_suspicious', False) else 'NO'])
            writer.writerow([])
            
            writer.writerow(['Digit', 'Observed', 'Expected', 'Deviation'])
            for digit in range(1, 10):
                obs = benford_result.get('observed_distribution', {}).get(digit, 0)
                exp = benford_result.get('expected_distribution', {}).get(digit, 0)
                dev = benford_result.get('deviations', {}).get(digit, 0)
                writer.writerow([digit, f"{obs:.4f}", f"{exp:.4f}", f"{dev:.4f}"])
            
            writer.writerow([])
            
            # Round number analysis
            writer.writerow(['ROUND NUMBER ANALYSIS'])
            writer.writerow(['Round Numbers (÷1000)', round_result.get('round_count', 0)])
            writer.writerow(['Percentage', f"{round_result.get('round_percentage', 0):.2f}%"])
            writer.writerow(['Very Round (÷10000)', round_result.get('very_round_count', 0)])
            writer.writerow(['Suspicious', 'YES' if round_result.get('is_suspicious', False) else 'NO'])
            writer.writerow([])
            
            # Top round numbers with citations
            writer.writerow(['TOP ROUND NUMBERS (with source citations)'])
            writer.writerow(['Amount', 'Source Document Hash', 'Page Number', 'Filename', 'Context'])
            
            round_amounts = round_result.get('round_amounts', [])
            for amount, doc_id, doc_hash, page_number, filename, context in sorted(round_amounts, key=lambda x: x[0], reverse=True)[:50]:
                writer.writerow([f"${amount:,.2f}", doc_hash, page_number, filename, context[:100]])
        
        print(f"Exported financial analysis report")
    
    def run_analysis(self, limit: int = None, output_dir: str = ".") -> None:
        """
        Run complete forensic accounting analysis.
        
        Args:
            limit: Optional limit on documents to process
            output_dir: Directory for output files
        """
        print("="*60)
        print("FORENSIC ACCOUNTANT - Financial Pattern Recognition")
        print("="*60)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load financial data
        self.load_financial_data(limit=limit)
        
        if not self.amounts:
            print("\nERROR: No financial amounts found. Cannot perform analysis.")
            return
        
        # Perform analyses
        benford_result = self.benford_test()
        round_result = self.round_number_analysis()
        
        # Export report
        report_path = Path(output_dir) / "financial_analysis_report.csv"
        self.export_report(benford_result, round_result, str(report_path))
        
        print("\n" + "="*60)
        print("Financial analysis complete!")
        print("="*60)


def main():
    """Main function for running forensic accounting analysis."""
    accountant = ForensicAccountant()
    accountant.run_analysis(output_dir="data/analysis_output")


if __name__ == "__main__":
    main()
