from flask import Blueprint, Flask, current_app, render_template
from typing import TYPE_CHECKING
import click
from pathlib import Path
from .models import DataFlow
from standard_pipelines.database import db

from .ff2hs_on_transcript.services import FF2HSOnTranscript
from .dialpad2zoho_on_transcript.services import Dialpad2ZohoOnTranscript
from .gmail_interval_followup.services import GmailIntervalFollowup
from .add_data_to_hubspot_field.services import AddDataToHubspotField
from .lead_followup_human_notification.services import LeadFollowupHumanNotification
from .append_hubspot_note.services import AppendHubspotNote

data_flow = Blueprint('data_flow', __name__)

from . import routes  # Import routes after blueprint creation

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    app.cli.add_command(init_flows)

@click.command('init-flows')
def init_flows():
    """Create DataFlow objects for flows listed in flows.txt if they don't exist."""
    flows_file = Path('flows.txt')
    
    if not flows_file.exists():
        current_app.logger.warning('flows.txt file not found')
        return
    
    # Read flows from file, skipping empty lines and comments
    flows = [
        line.strip() 
        for line in flows_file.read_text().splitlines() 
        if line.strip() and not line.startswith('#')
    ]
    
    for flow_name in flows:
        # Check if flow already exists
        existing_flow = DataFlow.query.filter_by(name=flow_name).first()
        
        if existing_flow:
            current_app.logger.info(f'Flow {flow_name} already exists')
            continue
            
        # Create new flow
        new_flow = DataFlow(
            name=flow_name,
            version='BLUE'  # for blue green deployment
        )
        db.session.add(new_flow)
        current_app.logger.info(f'Created new flow: {flow_name}')
    
    db.session.commit()
    current_app.logger.info('Finished creating flows')

from .ff2hs_on_transcript.models import FF2HSOnTranscriptConfiguration
from .lead_followup_human_notification.models import LeadFollowupHumanNotificationConfiguration
from .append_hubspot_note.models import AppendHubspotNoteConfiguration
from .dp2ss_on_transcript.models import DP2SSOnTranscriptConfiguration