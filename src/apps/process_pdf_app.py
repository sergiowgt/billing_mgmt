from dataclasses import dataclass
import copy
from datetime import datetime
import os
from typing import List
from src.domain.entities.response_error import UtilityBillDuplicatedResponse, UtilityBillErrorResponse, UtilityBillIgnoredResponse, UtilityBillOkResponse
from src.domain.enums.document_type_enum import DocumentTypeEnum
from src.domain.enums.service_provider_enum import ServiceProviderEnum

from src.infra.exception_handler import ApplicationException
from src.infra.google_drive_handler.Igoogle_drive_handler import IGoogleDriveHandler
from src.infra.pdf_extractor_handler.pdf_extractor_handler import PdfExtractorHandler
from src.infra.repositorios.accommodation_repository import AccommodationRepository
from src.infra.repositorios.exceptions_repository import ExceptionRepository
from src.infra.repositorios.paid_bill_repository import PaidBillRepository
from src.services.results_saver import ResultsSaver
from src.services.results_uploader import ResultsUploader
from src.services.utility_bill_factory import UtilityBillFactory


@dataclass
class ProcessPdfApp:
    _drive = None
    _log = None
    _in_analise_list = None
    _processed_list = None
    _not_found_list: List[UtilityBillErrorResponse] = None
    _error_list: List[UtilityBillErrorResponse] = None
    _expired_list: List[UtilityBillErrorResponse] = None
    _ignored_list: List[UtilityBillIgnoredResponse] = None
    _accommodations_repo: AccommodationRepository = None

    def __init__(self, drive: IGoogleDriveHandler, log, accommodations_repo: AccommodationRepository, paid_repo: PaidBillRepository, exception_repo: ExceptionRepository):
        ApplicationException.when(log is None, 'Log não iniciado.')
        ApplicationException.when(drive is None, 'Google Drive não iniciado.', log)
        self._drive = drive
        self._log = log
        self._processed_list = []
        self._in_analise_list = []
        self._error_list = []
        self._ignored_list = []
        self._not_found_list = []
        self._duplicate_list = []
        self._expired_list = []
        self._accommodations_repo = accommodations_repo
        self._paid_repo = paid_repo
        self._exception_repo = exception_repo

    def _service_provider_2_str(self, id: ServiceProviderEnum) -> str:
        if (id == ServiceProviderEnum.EDP):
            return '#EDP'
        if (id == ServiceProviderEnum.GALP):
            return '#GALP'
        if (id == ServiceProviderEnum.AGUAS_DE_PORTO):
            return '#AGUAS_PORTO'
        if (id == ServiceProviderEnum.AGUAS_DE_GAIA):
            return '#AGUAS_GAIA'
        if (id == ServiceProviderEnum.ALTICE_MEO):
            return '#ALTICE'
        if (id == ServiceProviderEnum.VODAFONE):
            return '#VODAFONE'
        if (id == ServiceProviderEnum.GOLDEN_ENERGY):
            return '#GOLD_ENERGY'
        if (id == ServiceProviderEnum.EPAL):
            return '#EPAL'
        if (id == ServiceProviderEnum.NOS):
            return '#NOS'

        return ''

    def _read_files(self, work_folder_id: str, email_local_folder: str) -> None:

        def process_file(all_text: str, file_name: str, file_id: str):
            conta_consumo = UtilityBillFactory().execute(all_text)
            if (conta_consumo):
                try:
                    conta_consumo.create(all_text)
                    if conta_consumo.tipo_documento == DocumentTypeEnum.DETALHE_FATURA:
                        self._ignored_list.append(UtilityBillIgnoredResponse(error_type='DETALHE_FATURA', email_file_id=file_id, google_file_id='', file_name=file_name))
                        self._log.info('===> Detalhe Fatura', instant_msg=True)
                    else:
                        self._in_analise_list.append(UtilityBillOkResponse(email_file_id=file_id, google_file_id='', file_name=file_name,
                                                                           utility_bill=conta_consumo))
                        self._log.info('===> Accepted', instant_msg=True)
                except Exception:
                    self._error_list.append(UtilityBillErrorResponse(error_type='ERRO_PROCESSAMENTO_PDF', email_file_id=file_id, google_file_id='',
                                                                     file_name=file_name, utility_bill=conta_consumo))
            else:
                self._ignored_list.append(UtilityBillIgnoredResponse(error_type='DETALHE_FATURA', email_file_id=file_id, google_file_id='', file_name=file_name))
                self._log.info('===> Ignored', instant_msg=True)

        def get_local_files(email_local_folder: str):
            for file_name in [f.upper() for f in os.listdir(email_local_folder) if os.path.isfile(os.path.join(email_local_folder, f)) and f.upper().endswith('.PDF') == True]:
                complete_file_name = os.path.join(email_local_folder, file_name)
                self._log.info(f'Processing file: {complete_file_name}')

                try:
                    all_text = PdfExtractorHandler().get_text(complete_file_name)
                except:
                    self._ignored_list.append(UtilityBillIgnoredResponse(error_type='PDF_INVALIDO', email_file_id='', google_file_id='', file_name=file_name))
                    self._log.info('===> Ignored (image)', instant_msg=True)
                    continue

                process_file(all_text, file_name, '')

        def get_remote_files(work_folder_id: str):
            files_in_drive = self._drive.get_files(work_folder_id)
            files = files_in_drive['files']
            total = len(files)
            count = 0
            for file in files:
                count = count + 1
                file_id = file['id']
                file_name = file['name']
                #str_aux = 'T_'
                #if (file_name[0:len(str_aux)].upper() != str_aux):
                #    continue
                #if (count > 15):  break

                self._log.info(f'Getting file: {file_name} ({file_id}) ({count}/{total})', instant_msg=True)
                file_content = self._drive.get_file(file_id)
                try:
                    all_text = PdfExtractorHandler().get_text(file_content)
                except:
                    self._ignored_list.append(UtilityBillIgnoredResponse(error_type='PDF_INVALIDO', email_file_id=file_id, google_file_id='', file_name=file_name))
                    self._log.info('===> Ignored (image)', instant_msg=True)
                    continue

                process_file(all_text, file_name, file_id)

        if email_local_folder:
            get_local_files(email_local_folder)
        else:
            get_remote_files(work_folder_id)````
            
        self._log.info(f'Total files => {self._processed_list``} {self._ignored_list}', instant_msg=True)

    def _is_duplicate(self, utility_bill) -> bool:
        for file in self._processed_list:
            if file.utility_bill == utility_bill:
                return True
        return False

    def _has_exceptions(self, file) -> bool:
        provider_name = self._service_provider_2_str(file.utility_bill.concessionaria)
        excep = self._exception_repo.get(file.utility_bill.id_alojamento, provider_name)

        if excep is None:
            return False

        nome_unico = file.utility_bill.nome_calculado
        except_type = excep[0]
        accomm_destination_list = excep[1]
        parcela = round(file.utility_bill.valor / len(accomm_destination_list), 2)

        if except_type == 1:
            for el in accomm_destination_list:
                new_file = copy.deepcopy(file)
                new_file.nome_calculado = nome_unico

                new_file.utility_bill.valor = parcela
                new_file.utility_bill.tipo_documento = DocumentTypeEnum.CONTA_CONSUMO_RATEIO
                new_file.utility_bill.id_alojamento = el
                self._processed_list.append(new_file)
        elif except_type == 2:
            self._error_list.append(UtilityBillErrorResponse(error_type='EXCEPTION_NAO_TRATADA', email_file_id=file.email_file_id, google_file_id='',
                                                             file_name=file.file_name, utility_bill=file.utility_bill))
        else:
            self._error_list.append(UtilityBillErrorResponse(error_type='EXCEPTION_NAO_TRATADA', email_file_id=file.email_file_id, google_file_id='',
                                                             file_name=file.file_name, utility_bill=file.utility_bill))
        return True

    def _check_utilities_bill(self) -> None:
        if (len(self._in_analise_list) == 0):
            return

        self._in_analise_list.sort(key=lambda x: x.utility_bill.str_valor, reverse=True)

        for file in self._in_analise_list:
            actual_bill = file.utility_bill
            print(f'Checking {file.file_name}...')

            if actual_bill.is_ok() is False:
                self._error_list.append(UtilityBillErrorResponse(error_type='INFOS_INCOMPLETAS', email_file_id=file.email_file_id, google_file_id='',
                                                                 file_name=file.file_name, utility_bill=actual_bill))
                continue

            # verifica se está duplicada no movimento
            if self._is_duplicate(utility_bill=actual_bill):
                self._duplicate_list.append(UtilityBillDuplicatedResponse(error_type='ARQUIVO_DUPLICADO', email_file_id=file.email_file_id, google_file_id='',
                                                                 file_name=file.file_name, utility_bill=actual_bill))
                
                continue

            # verifica se a alojamento existe
            accomm_aux = self._accommodations_repo.get(concessionaria=actual_bill.concessionaria,
                                                       cliente=actual_bill.id_cliente,
                                                       conta=actual_bill.id_conta,
                                                       contrato=actual_bill.id_contrato,
                                                       local=actual_bill.local_consumo,
                                                       instalacao=actual_bill.instalacao)

            if (accomm_aux is None):
                self._not_found_list.append(UtilityBillErrorResponse(error_type='ALOJAMENTO_INEXISTENTE', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                continue

            actual_bill.id_alojamento = accomm_aux._id
            actual_bill.folder_id = accomm_aux._folder_id
            actual_bill.folder_accounting_id = accomm_aux._folder_accounting_id.strip()
            # se a conta é anterior a data de lancamento
            if (actual_bill.dt_vencimento):
                if accomm_aux.is_valid_start_date(actual_bill.dt_vencimento) is False:
                    self._expired_list.append(UtilityBillErrorResponse(error_type='VCTO_ANTERIOR_DATA_LANCAMENTO', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                    continue

                if accomm_aux.is_closed(actual_bill.dt_vencimento):
                    self._expired_list.append(UtilityBillErrorResponse(error_type='MES_FECHADO(VCTO)', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                    continue

            elif (actual_bill.dt_emissao):
                if accomm_aux.is_valid_start_date(actual_bill.dt_emissao) is False:
                    self._expired_list.append(UtilityBillErrorResponse(error_type='EMISSAO_ANTERIOR_DATA_LANCAMENTO', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                    continue

                if accomm_aux.is_closed(actual_bill.dt_emissao):
                    self._expired_list.append(UtilityBillErrorResponse(error_type='MES_FECHADO(EMISSAO)', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                    continue

            if (actual_bill.tipo_documento == DocumentTypeEnum.NOTA_CREDITO) or (actual_bill.tipo_documento == DocumentTypeEnum.FATURA_ZERADA):
                if (actual_bill.dt_emissao is None):
                    self._error_list.append(UtilityBillErrorResponse(error_type='NC_OU_FATURA_ZERADA_SEM_DT_EMISSAO', email_file_id=file.email_file_id, google_file_id='',
                                                                     file_name=file.file_name, utility_bill=actual_bill))
                    continue

            # verifica se está pago
            paid = self._paid_repo.get(actual_bill.concessionaria, actual_bill.tipo_servico, actual_bill.id_alojamento, actual_bill.id_documento)
            if paid:
                dupl = UtilityBillDuplicatedResponse(error_type='CONTA_JA_PAGA', original_google_link=paid.original_file_id, email_file_id=file.email_file_id, google_file_id='',
                                                     file_name=file.file_name, utility_bill=actual_bill)
                self._duplicate_list.append(dupl)
                continue

            # verifica se a conta deve ir para  conciliacao
            actual_bill.is_accounting = accomm_aux.is_must_accounting(actual_bill.tipo_servico)

            # faz o rateio
            if self._has_exceptions(file):
                continue

            file.nome_calculado = actual_bill.nome_calculado
            self._processed_list.append(file)

    def _clean_email_folder(self):
        def get_unique_email_id_list() -> List:
            unique_list = []
            for file in self._processed_list:
                if file.email_file_id not in unique_list:
                    unique_list.append(file.email_file_id)

            return unique_list

        def delete_file(msg: str, file_id: str):
            self._log.info(msg, instant_msg=True)
            self._drive.delete_file(file_id=file_id)

        self._log.info('Cleaning up email folder', instant_msg=True)
        for file_id in get_unique_email_id_list():
            try:
                delete_file(msg=f'Cleaning processed file {file_id}', file_id=file_id)
            except Exception as error:
                self._log.info(f'Erro {str(error)}', instant_msg=True)

        for file in self._ignored_list:
            delete_file(msg=f'Cleaning ignored file {file.file_name} ({file.email_file_id})', file_id=file.email_file_id)

        for file in self._duplicate_list:
            delete_file(msg=f'Cleaning duplicated file {file.file_name} ({file.email_file_id})', file_id=file.email_file_id)


    def _upload_files(self, others_folder_base_id: str) -> None:
        uploader = ResultsUploader(self._log, self._drive)

        self._log.info('Uploading list of processed', instant_msg=True)
        uploader.upload_ok_list_new(self._processed_list)
        self._log.info(f'{len(self._processed_list)} file(s) processed', instant_msg=True)

        self._log.info('Uploading list of unprocessed ', instant_msg=True)
        uploader.upload_other_list(others_folder_base_id, self._not_found_list, self._error_list, self._expired_list,  self._duplicate_list, self._ignored_list)
        self._log.info(f'{len(self._not_found_list)} file(s) without accommodation', instant_msg=True)
        self._log.info(f'{len(self._error_list)} error file(s)', instant_msg=True)
        self._log.info(f'{len(self._expired_list)} expired bill file(s)', instant_msg=True)
        self._log.info(f'{len(self._duplicate_list)} duplicate file(s)', instant_msg=True)
        self._log.info(f'{len(self._ignored_list)} ignored file(s)', instant_msg=True)

    def _export_results(self, results_folder_id, exports_folder, qd28_path, paid_bill_path):
        now = datetime.now()
        export_filename = f'output_{now.strftime("%Y-%m-%d.%H.%M.%S")}.xlsx'
        export_filename = os.path.join(exports_folder, export_filename)

        self._log.info('Saving the worksheets', instant_msg=True)
        saver = ResultsSaver(self._log, self._drive)
        saver.execute(export_filename, qd28_path, paid_bill_path, self._processed_list, self._not_found_list,
                      self._error_list,  self._expired_list, self._duplicate_list, self._ignored_list, self._paid_repo.count+1)

        self._log.info('Upload results', instant_msg=True)
        uploader = ResultsUploader(self._log, self._drive)
        uploader.upload_results(results_folder_id, export_filename)
        uploader.upload_excelfile(results_folder_id, paid_bill_path, 'historic')
        uploader.upload_excelfile('1Q1L3zvZZzQ3-BrQdetGU60PY3dGr2ECX', qd28_path, '')

    def execute(self, work_folder_id: str, email_local_folder: str, others_folder_base_id: str, results_folder_id: str, qd28_path: str, paid_bill_path: str, exports_folder: str):
        # Aqui le os arquivos e os separa em com erro, ignorados e em analise
        self._read_files(work_folder_id, email_local_folder)

        # Criar uma rotina que pega os arquivos em análise e joga nas listas corretas od já pagos, duplicados, com erro, e nos avisos do clovis
        self._check_utilities_bill()

        # Rotina para subir os arquivos das contas(igual do antigo)
        self._upload_files(others_folder_base_id)

        # Rotina para subir os arquivos de resultados (igual ao antigo)
        self._export_results(results_folder_id, exports_folder, qd28_path, paid_bill_path)

        # Rotina para para excluir os emails
        self._clean_email_folder()

        # resumo
        print(f'Sem alojamentos {len(self._not_found_list)}, OK {len(self._processed_list)}, Ignorados {len(self._ignored_list)}, Erros {len(self._error_list)}, Duplicados {len(self._duplicate_list)} ')


# sergiowgt.teste@gmail.com
# qrsatvqbzwoddmbj
