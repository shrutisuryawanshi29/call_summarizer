"""Export transcripts and summaries to various formats."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


class Exporter:
    """Exports transcripts and summaries to files."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize exporter.
        
        Args:
            output_dir: Output directory. Defaults to ~/CallSummaries
        """
        if output_dir is None:
            output_dir = Path.home() / "CallSummaries"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_transcript(self, transcript: str, timestamp: Optional[datetime] = None) -> Path:
        """Export transcript to text file.
        
        Args:
            transcript: Full transcript text
            timestamp: Meeting timestamp. Defaults to now
            
        Returns:
            Path to saved file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_transcript.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript\n")
            f.write(f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(transcript)
        
        return filepath
    
    def export_summary_markdown(self, summary: Dict, timestamp: Optional[datetime] = None) -> Path:
        """Export summary to Markdown file.
        
        Args:
            summary: Summary dictionary
            timestamp: Meeting timestamp. Defaults to now
            
        Returns:
            Path to saved file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_summary.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Meeting Summary\n\n")
            f.write(f"**Date:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"{'='*60}\n\n")
            
            # Overall summary
            if 'summary' in summary:
                f.write(f"## Overview\n\n{summary['summary']}\n\n")
            
            # Key points
            if 'key_points' in summary and summary['key_points']:
                f.write(f"## Key Points\n\n")
                for point in summary['key_points']:
                    f.write(f"- {point}\n")
                f.write("\n")
            
            # Decisions
            if 'decisions' in summary and summary['decisions']:
                f.write(f"## Decisions\n\n")
                for decision in summary['decisions']:
                    f.write(f"- {decision}\n")
                f.write("\n")
            
            # Action items
            if 'action_items' in summary and summary['action_items']:
                f.write(f"## Action Items\n\n")
                for item in summary['action_items']:
                    if isinstance(item, dict):
                        task = item.get('task', 'N/A')
                        assignee = item.get('assignee', 'TBD')
                        deadline = item.get('deadline', 'TBD')
                        f.write(f"- **{task}**\n")
                        f.write(f"  - Assignee: {assignee}\n")
                        f.write(f"  - Deadline: {deadline}\n")
                    else:
                        f.write(f"- {item}\n")
                f.write("\n")
            
            # People mentioned
            if 'people_mentioned' in summary and summary['people_mentioned']:
                f.write(f"## People Mentioned\n\n")
                for person in summary['people_mentioned']:
                    f.write(f"- {person}\n")
                f.write("\n")
            
            # Topics
            if 'topics' in summary and summary['topics']:
                f.write(f"## Topics Discussed\n\n")
                for topic in summary['topics']:
                    f.write(f"- {topic}\n")
                f.write("\n")
        
        return filepath
    
    def export_summary_pdf(self, summary: Dict, transcript: Optional[str] = None, 
                          timestamp: Optional[datetime] = None) -> Path:
        """Export summary to PDF file.
        
        Args:
            summary: Summary dictionary
            transcript: Optional full transcript
            timestamp: Meeting timestamp. Defaults to now
            
        Returns:
            Path to saved file
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
        except ImportError:
            raise ImportError("reportlab not installed. Install with: pip install reportlab")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_summary.pdf"
        filepath = self.output_dir / filename
        
        # Create PDF
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#1a1a1a',
            spaceAfter=12,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Meeting Summary", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        date_style = ParagraphStyle(
            'CustomDate',
            parent=styles['Normal'],
            fontSize=10,
            textColor='#666666',
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", date_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Overall summary
        if 'summary' in summary:
            heading_style = ParagraphStyle(
                'SectionHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor='#2c3e50',
                spaceAfter=6
            )
            story.append(Paragraph("Overview", heading_style))
            story.append(Paragraph(summary['summary'], styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Key points
        if 'key_points' in summary and summary['key_points']:
            story.append(Paragraph("Key Points", styles['Heading2']))
            for point in summary['key_points']:
                story.append(Paragraph(f"• {point}", styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        # Decisions
        if 'decisions' in summary and summary['decisions']:
            story.append(Paragraph("Decisions", styles['Heading2']))
            for decision in summary['decisions']:
                story.append(Paragraph(f"• {decision}", styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        # Action items
        if 'action_items' in summary and summary['action_items']:
            story.append(Paragraph("Action Items", styles['Heading2']))
            for item in summary['action_items']:
                if isinstance(item, dict):
                    task = item.get('task', 'N/A')
                    assignee = item.get('assignee', 'TBD')
                    deadline = item.get('deadline', 'TBD')
                    story.append(Paragraph(f"<b>{task}</b>", styles['Normal']))
                    story.append(Paragraph(f"  Assignee: {assignee} | Deadline: {deadline}", 
                                         styles['Normal']))
                else:
                    story.append(Paragraph(f"• {item}", styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        # People mentioned
        if 'people_mentioned' in summary and summary['people_mentioned']:
            story.append(Paragraph("People Mentioned", styles['Heading2']))
            for person in summary['people_mentioned']:
                story.append(Paragraph(f"• {person}", styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        # Topics
        if 'topics' in summary and summary['topics']:
            story.append(Paragraph("Topics Discussed", styles['Heading2']))
            for topic in summary['topics']:
                story.append(Paragraph(f"• {topic}", styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
        
        # Full transcript (if provided)
        if transcript:
            story.append(PageBreak())
            story.append(Paragraph("Full Transcript", styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            # Split transcript into paragraphs
            paragraphs = transcript.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def export_mini_summary(self, bullets: List[str], timestamp: Optional[datetime] = None) -> str:
        """Format mini-summary bullets as text.
        
        Args:
            bullets: List of bullet points
            timestamp: Meeting timestamp. Defaults to now
            
        Returns:
            Formatted mini-summary text
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        text = f"[{timestamp.strftime('%H:%M:%S')}] Recent Updates:\n"
        for bullet in bullets:
            text += f"  • {bullet}\n"
        
        return text

