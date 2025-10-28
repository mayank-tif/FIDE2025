from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging
from .models import *
import logging
from FWC2025.env_details import *


logger = logging.getLogger(SCHEDULE_LOGGER_NAME)


def send_transportation_email_scheduler():
    """
    Scheduler function to check roasters with is_email_sent=False and send emails to players
    """
    try:
        print("Starting transportation email scheduler...")
        logger.info("Starting transportation email scheduler...")
        
        # Get roasters that haven't had emails sent yet
        pending_roasters = Roaster.objects.filter(
            is_email_sent=False, 
            status_flag=1
        ).prefetch_related('playertransportationdetails_set__playerId')
        
        if not pending_roasters.exists():
            print("No pending roasters found for email sending.")
            return {
                'success': True,
                'message': 'No pending roasters found.',
                'roasters_processed': 0,
                'emails_sent': 0
            }
        
        total_emails_sent = 0
        roasters_processed = 0
        
        print(f"Found {pending_roasters.count()} roasters with pending emails")
        logger.info(f"Found {pending_roasters.count()} roasters with pending emails")
        
        for roaster in pending_roasters:
            try:
                # Get all transportation details for this roaster
                transport_details = PlayerTransportationDetails.objects.filter(
                    roasterId=roaster,
                    status_flag=1
                ).select_related('playerId')
                
                if not transport_details.exists():
                    print(f" No players found for roaster: {roaster.vechicle_type} - {roaster.vechicle_no}")
                    # Mark as email sent even if no players to avoid reprocessing
                    roaster.is_email_sent = True
                    roaster.save()
                    continue
                
                emails_sent_for_roaster = 0
                print(f"Processing roaster: '{roaster.vechicle_type} - {roaster.vechicle_no}' with {transport_details.count()} players")
                
                # Send email to each player in this roaster
                for transport_detail in transport_details:
                    if transport_detail.playerId and transport_detail.playerId.email:
                        success = _send_single_transportation_email(transport_detail)
                        if success:
                            emails_sent_for_roaster += 1
                            total_emails_sent += 1
                
                # Mark roaster as email_sent if we sent at least one email
                if emails_sent_for_roaster > 0:
                    roaster.is_email_sent = True
                    roaster.updated_on = timezone.now()
                    roaster.save()
                    roasters_processed += 1
                    logger.info(f" SUCCESS: Processed roaster '{roaster.vechicle_type} - {roaster.vechicle_no}': {emails_sent_for_roaster} emails sent")
                    
                    print(f" SUCCESS: Processed roaster '{roaster.vechicle_type} - {roaster.vechicle_no}': {emails_sent_for_roaster} emails sent")
                else:
                    logger.warning(f" WARNING: No emails sent for roaster: {roaster.vechicle_type} - {roaster.vechicle_no}")
                    print(f" WARNING: No emails sent for roaster: {roaster.vechicle_type} - {roaster.vechicle_no}")
                    # Still mark as sent to avoid infinite retries for problematic roasters
                    roaster.is_email_sent = True
                    roaster.save()
                    
            except Exception as e:
                logger.error(f" ERROR processing roaster {roaster.id}: {str(e)}")
                print(f" ERROR processing roaster {roaster.id}: {str(e)}")
                # Mark as sent to avoid repeated failures
                roaster.is_email_sent = True
                roaster.save()
                continue
        
        print(f"COMPLETED: Processed {roasters_processed} roasters, sent {total_emails_sent} emails")
        logger.info(f"Processed {roasters_processed} roasters, sent {total_emails_sent} emails")
        return {
            'success': True,
            'message': f'Processed {roasters_processed} roasters, sent {total_emails_sent} emails',
            'roasters_processed': roasters_processed,
            'emails_sent': total_emails_sent
        }
        
    except Exception as e:
        error_msg = f" CRITICAL ERROR in transportation email scheduler: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return {
            'success': False,
            'message': error_msg,
            'roasters_processed': 0,
            'emails_sent': 0
        }


def _send_single_transportation_email(transport_detail):
    """
    Send transportation email to a single player
    """
    try:
        player = transport_detail.playerId
        roaster = transport_detail.roasterId
        
        # Prepare all the data for the email
        player_name = player.name or "Player"
        player_fide_id = player.fide_id or "N/A"
        player_email = player.email
        travel_date = roaster.travel_date.strftime("%B %d, %Y at %I:%M %p") if roaster.travel_date else "Not specified"
        vehicle_type = roaster.vechicle_type or "Not specified"
        vehicle_number = roaster.vechicle_no or "Not specified"
        driver_name = roaster.driver_name or "Not specified"
        driver_phone = roaster.mobile_no or "Not specified"
        number_of_seats = roaster.number_of_seats or "Not specified"
        
        # Get pickup and drop locations
        pickup_location = roaster.pickup_location_custom if roaster.pickup_location == Roaster.LOCATION_OTHER else roaster.get_pickup_location_display()
        drop_location = roaster.drop_location_custom if roaster.drop_location == Roaster.LOCATION_OTHER else roaster.get_drop_location_display()
        
        # Get current status with proper display
        current_status = transport_detail.player_status_display or transport_detail.get_entry_status_display()
        
        # Get transportation type if available
        transportation_type = ""
        if transport_detail.transportationTypeId:
            transportation_type = transport_detail.transportationTypeId.name

        # Create HTML content directly
        html_message = f"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Transportation Details - FWC 2025</title>
  <style type="text/css">
    a, a[href], a:hover, a:link, a:visited {{
      text-decoration: none!important;
      color: #0000EE;
    }}
    .link {{
      text-decoration: underline!important;
    }}
    p, p:visited {{
      font-size: 15px;
      line-height: 24px;
      font-family: 'Helvetica', Arial, sans-serif;
      font-weight: 300;
      text-decoration: none;
      color: #000000;
    }}
    h1 {{
      font-size: 22px;
      line-height: 24px;
      font-family: 'Helvetica', Arial, sans-serif;
      font-weight: normal;
      text-decoration: none;
      color: #000000;
    }}
    h2 {{
      font-size: 18px;
      line-height: 22px;
      font-family: 'Helvetica', Arial, sans-serif;
      font-weight: 600;
      text-decoration: none;
      color: #241A4F;
    }}
    .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td {{
      line-height: 100%;
    }}
    .ExternalClass {{
      width: 100%;
    }}
    .info-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }}
    .info-table td {{
      padding: 12px;
      border: 1px solid #ddd;
      text-align: left;
      vertical-align: top;
    }}
    .info-table .label {{
      font-weight: bold;
      background-color: #f9f9f9;
      width: 35%;
    }}
    .transport-box {{
      background-color: #f0f8ff;
      padding: 20px;
      border-left: 4px solid #241A4F;
      margin: 20px 0;
      border-radius: 8px;
    }}
    .player-info {{
      background-color: #e8f4fd;
      padding: 20px;
      border-radius: 8px;
      margin: 20px 0;
    }}
    .status-badge {{
      background-color: #28a745;
      color: white;
      padding: 6px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
      display: inline-block;
    }}
    .route-info {{
      background-color: #fff3cd;
      padding: 15px;
      border-radius: 8px;
      margin: 20px 0;
      border-left: 4px solid #ffc107;
    }}
    .vehicle-info {{
      background-color: #d4edda;
      padding: 15px;
      border-radius: 8px;
      margin: 20px 0;
      border-left: 4px solid #28a745;
    }}
  </style>
</head>
<body style="text-align: center; margin: 0; padding-top: 10px; padding-bottom: 10px; padding-left: 0; padding-right: 0; -webkit-text-size-adjust: 100%;background-color: #241A4F; color: #000000" align="center">
  <div style="text-align: center;">
    <table align="center" style="text-align: center; vertical-align: top; width: 600px; max-width: 600px; background-color: #ffffff;" width="600">
      <tbody>
        <tr>
          <td style="width: 596px; vertical-align: top; padding-left: 0; padding-right: 0; width="596">
            <img style="width: 600px; max-width: 595px; height: 350px; max-height: 350px; text-align: center;" alt="FWC image" src="https://dashboard.fwc2025.in/static/email/new_email_logo.jpg" align="center" width="600" height="350">
          </td>
        </tr>
      </tbody>
    </table>
    <table align="center" style="text-align: center; vertical-align: top; width: 600px; max-width: 600px; background-color: #ffffff;" width="600">
      <tbody>
        <tr>
          <td style="width: 596px; vertical-align: top; padding-left: 30px; padding-right: 30px; padding-top: 30px; padding-bottom: 40px;" width="596">
            <h1 style="font-size: 24px; line-height: 28px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 600; text-decoration: none; color: #241A4F; margin-bottom: 10px;">
              🚗 Transportation Details
            </h1>
            <span class="status-badge">TRANSPORT SCHEDULED</span>
            <p style="font-size: 16px; line-height: 24px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 400; text-decoration: none; color: #333333; margin-bottom: 30px;">
              Your transportation details for FWC 2025 have been confirmed. Please review the information below.
            </p>
            <div class="player-info">
              <h2 style="font-size: 18px; line-height: 22px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 600; text-decoration: none; color: #241A4F; margin-top: 0;">
                Player Information
              </h2>
              <table style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td style="padding: 10px 0; border-bottom: 1px solid #cce7ff; text-align: left; font-weight: bold; width: 40%;">Player Name:</td>
                  <td style="padding: 10px 0; border-bottom: 1px solid #cce7ff; text-align: left;">{player_name}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; border-bottom: 1px solid #cce7ff; text-align: left; font-weight: bold;">FIDE ID:</td>
                  <td style="padding: 10px 0; border-bottom: 1px solid #cce7ff; text-align: left;">{player_fide_id}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 0; text-align: left; font-weight: bold;">Email:</td>
                  <td style="padding: 10px 0; text-align: left;">{player_email}</td>
                </tr>
              </table>
            </div>
            <div class="route-info">
              <h2 style="font-size: 18px; line-height: 22px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 600; text-decoration: none; color: #856404; margin-top: 0;">
                🗺️ Route Information
              </h2>
              <table style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold; width: 40%;">From:</td>
                  <td style="padding: 8px 0; text-align: left; font-size: 16px;">{pickup_location}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">To:</td>
                  <td style="padding: 8px 0; text-align: left; font-size: 16px;">{drop_location}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">Travel Date & Time:</td>
                  <td style="padding: 8px 0; text-align: left; font-size: 16px;"><strong>{travel_date}</strong></td>
                </tr>
              </table>
            </div>
            <div class="vehicle-info">
              <h2 style="font-size: 18px; line-height: 22px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 600; text-decoration: none; color: #155724; margin-top: 0;">
                🚙 Vehicle Details
              </h2>
              <table style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold; width: 40%;">Vehicle Type:</td>
                  <td style="padding: 8px 0; text-align: left;">{vehicle_type}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">Vehicle Number:</td>
                  <td style="padding: 8px 0; text-align: left;">{vehicle_number}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">Driver Name:</td>
                  <td style="padding: 8px 0; text-align: left;">{driver_name}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">Driver Contact:</td>
                  <td style="padding: 8px 0; text-align: left;">{driver_phone}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; text-align: left; font-weight: bold;">Seating Capacity:</td>
                  <td style="padding: 8px 0; text-align: left;">{number_of_seats} seats</td>
                </tr>
              </table>
            </div>
            <div class="transport-box">
              <h2 style="font-size: 18px; line-height: 22px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 600; text-decoration: none; color: #241A4F; margin-top: 0;">
                📋 Journey Details
              </h2>
              <table class="info-table">
                <tr>
                  <td class="label">Current Status:</td>
                  <td><strong style="color: #28a745;">{current_status}</strong></td>
                </tr>
              </table>
            </div>
            </div>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            <p style="font-size: 12px; line-height: 16px; font-family: 'Helvetica', Arial, sans-serif; font-weight: 300; text-decoration: none; color: #919293;">
              This email was automatically generated by the FIDE World Cup 2025 App.
            </p>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
        """

        subject = f"Transportation Details - {player_name} - FWC 2025"

        # Create email log
        try:
            email_log = EmailLog.objects.create(
                email_type='TRANSPORTATION_DETAILS',
                subject=subject,
                recipient_email=player_email,
                status='PENDING',
                html_content=html_message,
                text_content=f"Transportation details for {player_name}",
            )
        except Exception as log_error:
            logger.error(f"Failed to create email log for {player_email}: {str(log_error)}")
            print(f"WARNING: Failed to create email log for {player_email}: {str(log_error)}")

        # Send email
        send_mail(
            subject=subject,
            message=f"""""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[player_email],
            html_message=html_message,
            fail_silently=False,
        )

        # Update email log status
        if 'email_log' in locals():
            email_log.status = 'SENT'
            email_log.sent_at = timezone.now()
            email_log.save()
        
        print(f"SUCCESS: Transportation email sent to {player_email}")  
        logger
        return True

    except Exception as e:
        logger.error(f"FAILED to send transportation email to {player_email}: {str(e)}")
        print(f"FAILED to send transportation email to {player_email}: {str(e)}")
        
        # Update email log status to failed
        if 'email_log' in locals():
            email_log.status = 'FAILED'
            email_log.error_message = str(e)
            email_log.save()
            
        return False