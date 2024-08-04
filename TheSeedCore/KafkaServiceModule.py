# -*- coding: utf-8 -*-
"""
TheSeedCore KafkaService Module

Module Description:
This module provides a comprehensive service for managing Apache Kafka clusters.
It includes functionalities for adding and configuring clusters, creating producers and consumers, managing Kafka topics, and handling message sending and receiving.
The module ensures robust error handling and logging for all operations, and it is designed to support future extensions for additional Kafka-related functionalities.

Main Components:
1. Dependency Check and Import: Checks and imports necessary modules and libraries such as kafka-python.
2. Logger Setup: Configures a default logger for Kafka service operations to handle logging of operations and errors.
3. KafkaService Class: Manages Kafka clusters, producers, and consumers, providing methods to perform various Kafka operations.

Module Functionality Overview:
- Manages Kafka clusters including adding clusters, updating configurations, and monitoring cluster health.
- Creates and manages Kafka producers and consumers for different clusters.
- Supports creation, listing, and configuration of Kafka topics.
- Handles sending and receiving messages with detailed logging and error handling.
- Provides utility functions to manage offsets and consumer groups.
- Ensures compatibility with various Kafka configurations and settings.

Key Classes and Methods:
- _checkDependencies(): Checks and imports module dependencies.
- defaultLogger(): Configures and returns a logger for Kafka service operations.
- KafkaService: Core class for managing Kafka clusters and operations.
  - addCluster(): Adds a new Kafka cluster with optional admin configurations.
  - updateClusterConfig(): Updates the configuration for a specific Kafka cluster.
  - monitorCluster(): Monitors the status of a specific Kafka cluster.
  - createProducer(): Creates a Kafka producer for a specific cluster.
  - createConsumer(): Creates a Kafka consumer for a specific cluster.
  - createTopic(): Creates a Kafka topic in a specific cluster.
  - sendMessage(): Sends a message to a Kafka topic.
  - receiveMessage(): Receives messages from a Kafka topic.
  - onSendSuccess(): Callback for successful message sending.
  - onSendError(): Callback for errors in message sending.
  - closeSingleProducer(): Closes a specific Kafka producer.
  - closeSingleConsumer(): Closes a specific Kafka consumer.
  - closeAllProducers(): Closes all producers in a specific cluster.
  - closeAllConsumers(): Closes all consumers in a specific cluster.
  - closeAllClusters(): Closes all clusters and their producers and consumers.
  - getProducer(): Retrieves a specific Kafka producer.
  - getConsumer(): Retrieves a specific Kafka consumer.
  - listTopics(): Lists all topics in a specific cluster.
  - listConsumerGroups(): Lists all consumer groups in a specific cluster.
  - describeConsumerGroup(): Describes a specific consumer group.
  - alterTopicConfig(): Alters the configuration of a specific Kafka topic.
  - getOffsets(): Retrieves offsets for a specific topic partition.
  - setOffsets(): Sets offsets for a specific topic partition.
  - checkHealth(): Checks the health of a specific Kafka cluster.

Notes:
- Ensure all necessary dependencies (kafka-python, etc.) are installed before using this module.
- Configure Kafka cluster parameters appropriately in the addCluster and updateClusterConfig methods.
- Utilize the KafkaService class to manage Kafka clusters and perform various operations.
- Refer to the logging output for detailed information on Kafka operations and errors.
"""

from __future__ import annotations

import logging
import pickle
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

_KafkaSupport = False


def _checkDependencies():
    global _KafkaSupport
    try:
        # noinspection PyUnresolvedReferences
        from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient, TopicPartition
        # noinspection PyUnresolvedReferences
        from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
        _KafkaSupport = True
    except ImportError as _:
        _KafkaSupport = False


_checkDependencies()


def defaultLogger(debug_mode: bool = False) -> logging.Logger:
    logger = logging.getLogger(f'TheSeedCore - KafkaService')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    if debug_mode:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

    formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


if _KafkaSupport:
    # noinspection PyUnresolvedReferences
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient, TopicPartition
    # noinspection PyUnresolvedReferences
    from kafka.admin import NewTopic, ConfigResource, ConfigResourceType


    class KafkaService:
        INSTANCE: KafkaService = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, *args, **kwargs):
            if cls.INSTANCE is None:
                cls.INSTANCE = super(KafkaService, cls).__new__(cls)
            return cls.INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if not self._INITIALIZED:
                self._Logger = defaultLogger(DebugMode) if Logger is None else Logger
                self._Clusters: Dict[str, Dict[str, Any]] = {}
                KafkaService._INITIALIZED = True

        def addCluster(self, cluster_id: str, admin_configs: Optional[Dict[str, Any]] = None):
            if cluster_id not in self._Clusters:
                self._Clusters[cluster_id] = {
                    "producers": {},
                    "consumers": {},
                    "admin_client": KafkaAdminClient(**admin_configs) if admin_configs else None
                }
                self._Logger.info(f"Cluster {cluster_id} added.")

        def updateClusterConfig(self, cluster_id: str, new_admin_configs: Dict[str, Any]):
            """更新集群配置"""
            if cluster_id in self._Clusters:
                try:
                    self._Clusters[cluster_id]["admin_client"].close()
                    self._Clusters[cluster_id]["admin_client"] = KafkaAdminClient(**new_admin_configs)
                    self._Logger.info(f"Cluster {cluster_id} configuration updated.")
                except Exception as e:
                    self._Logger.error(f"Updating cluster {cluster_id} configuration failed: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Update cluster config failed: Cluster {cluster_id} not found.")

        def monitorCluster(self, cluster_id: str):
            """监控集群状态"""
            if cluster_id in self._Clusters:
                try:
                    admin_client = self._Clusters[cluster_id]["admin_client"]
                    if admin_client:
                        metrics = admin_client.metrics()
                        self._Logger.info(f"Cluster {cluster_id} metrics: {metrics}")
                        return metrics
                    else:
                        self._Logger.error(f"Monitor cluster failed: No admin client found for cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Error during monitoring cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Monitor cluster failed: Cluster {cluster_id} not found.")
            return None

        def createProducer(self, cluster_id: str, client_id: str, **configs):
            if cluster_id in self._Clusters:
                configs["client_id"] = client_id
                producer = KafkaProducer(**configs)
                self._Clusters[cluster_id]["producers"][client_id] = producer
                self._Logger.info(f"Producer created for client_id: {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Create producer failed: Cluster {cluster_id} not found.")

        def createConsumer(self, cluster_id: str, client_id: str, topics: List[str], **configs):
            if cluster_id in self._Clusters:
                configs["client_id"] = client_id
                consumer = KafkaConsumer(*topics, **configs)
                self._Clusters[cluster_id]["consumers"][client_id] = consumer
                self._Logger.info(f"Consumer created for client_id: {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Create consumer failed: Cluster {cluster_id} not found.")

        def createTopic(self, cluster_id: str, topic_name: str, num_partitions: int, replication_factor: int, **configs):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        topic = NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor, **configs)
                        admin_client.create_topics([topic])
                        self._Logger.debug(f"Topic {topic_name} created in cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Creating topic {topic_name} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Create topic failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Create topic failed: Cluster {cluster_id} not found.")

        def sendMessage(self, cluster_id: str, client_id: str, topic: str, data: Any):
            if cluster_id in self._Clusters:
                producer = self._Clusters[cluster_id]["producers"].get(client_id)
                if producer:
                    serialized_data = pickle.dumps(data)
                    producer.send(topic, value=serialized_data).add_callback(self.onSendSuccess).add_errback(self.onSendError)
                    self._Logger.info(f"Message sent to topic {topic} by producer {client_id} in cluster {cluster_id}")
                else:
                    self._Logger.error(f"Send message failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Send message failed: Cluster {cluster_id} not found.")

        def receiveMessage(self, cluster_id: str, client_id: str, msg_callback):
            if cluster_id in self._Clusters:
                consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
                if consumer:
                    for msg in consumer:
                        data = pickle.loads(msg.value)
                        msg_callback(data)
                    self._Logger.info(f"Messages received by consumer {client_id} in cluster {cluster_id}")
                else:
                    self._Logger.error(f"Receive message failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Receive message failed: Cluster {cluster_id} not found.")

        def onSendSuccess(self, record_metadata):
            self._Logger.info(f"Message sent successfully: {record_metadata.topic} - {record_metadata.partition} - {record_metadata.offset}")

        def onSendError(self, exception):
            self._Logger.error(f"Error sending message: {exception}")

        def closeSingleProducer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                producer = self._Clusters[cluster_id]["producers"].get(client_id)
                if producer:
                    try:
                        producer.close()
                        del self._Clusters[cluster_id]["producers"][client_id]
                        self._Logger.info(f"Producer {client_id} closed and removed from cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Close producer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Close producer failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Close producer failed: Cluster {cluster_id} not found.")

        def closeSingleConsumer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
                if consumer:
                    try:
                        consumer.close()
                        del self._Clusters[cluster_id]["consumers"][client_id]
                        self._Logger.info(f"Consumer {client_id} closed and removed from cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Close consumer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Close consumer failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Close consumer failed: Cluster {cluster_id} not found.")

        def closeAllProducers(self, cluster_id: str):
            if cluster_id in self._Clusters:
                for client_id in list(self._Clusters[cluster_id]["producers"].keys()):
                    self.closeSingleProducer(cluster_id, client_id)
            else:
                self._Logger.error(f"Close all producers failed: Cluster {cluster_id} not found.")

        def closeAllConsumers(self, cluster_id: str):
            if cluster_id in self._Clusters:
                for client_id in list(self._Clusters[cluster_id]["consumers"].keys()):
                    self.closeSingleConsumer(cluster_id, client_id)
            else:
                self._Logger.error(f"Close all consumers failed: Cluster {cluster_id} not found.")

        def closeAllClusters(self):
            for cluster_id in list(self._Clusters.keys()):
                self.closeAllProducers(cluster_id)
                self.closeAllConsumers(cluster_id)
                self._Clusters[cluster_id]["admin_client"].close()
                del self._Clusters[cluster_id]
            self._Logger.info("All clusters closed and removed.")

        def getProducer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                try:
                    return self._Clusters[cluster_id]["producers"][client_id]
                except KeyError:
                    raise ValueError(f"Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                raise ValueError(f"Cluster {cluster_id} not found.")

        def getConsumer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                try:
                    return self._Clusters[cluster_id]["consumers"][client_id]
                except KeyError:
                    raise ValueError(f"Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                raise ValueError(f"Cluster {cluster_id} not found.")

        def listTopics(self, cluster_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        topics = admin_client.list_topics()
                        self._Logger.info(f"Available topics in cluster {cluster_id}: {topics}")
                        return topics
                    except Exception as e:
                        self._Logger.error(f"Error listing topics in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"List topics failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"List topics failed: Cluster {cluster_id} not found.")
            return []

        def listConsumerGroups(self, cluster_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        consumer_groups = admin_client.list_consumer_groups()
                        self._Logger.info(f"Consumer groups in cluster {cluster_id}: {consumer_groups}")
                        return consumer_groups
                    except Exception as e:
                        self._Logger.error(f"Error listing consumer groups in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"List consumer groups failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"List consumer groups failed: Cluster {cluster_id} not found.")
            return []

        def describeConsumerGroup(self, cluster_id: str, group_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        group_description = admin_client.describe_consumer_groups([group_id])
                        self._Logger.info(f"Description for group {group_id} in cluster {cluster_id}: {group_description}")
                        return group_description
                    except Exception as e:
                        self._Logger.error(f"Error describing consumer group {group_id} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Describe consumer group failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Describe consumer group failed: Cluster {cluster_id} not found.")
            return {}

        def alterTopicConfig(self, cluster_id: str, topic_name: str, config: Dict[str, str]):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        config_resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
                        config_entries = {k: v for k, v in config.items()}
                        admin_client.alter_configs({config_resource: config_entries})
                        self._Logger.info(f"Config for topic {topic_name} updated in cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Error altering topic config for {topic_name} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Alter topic config failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Alter topic config failed: Cluster {cluster_id} not found.")

        def getOffsets(self, cluster_id: str, topic_name: str, partition: int):
            if cluster_id in self._Clusters:
                try:
                    consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                    if not consumer:
                        consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                        self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                    tp = TopicPartition(topic_name, partition)
                    offsets = consumer.end_offsets([tp])
                    self._Logger.info(f"Offsets for {topic_name} partition {partition} in cluster {cluster_id}: {offsets[tp]}")
                    return offsets[tp]
                except Exception as e:
                    self._Logger.error(f"Error getting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Get offsets failed: Cluster {cluster_id} not found.")
            return None

        def setOffsets(self, cluster_id: str, topic_name: str, partition: int, offset: int):
            if cluster_id in self._Clusters:
                try:
                    consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                    if not consumer:
                        consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                        self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                    tp = TopicPartition(topic_name, partition)
                    consumer.seek(tp, offset)
                    self._Logger.info(f"Offset for {topic_name} partition {partition} set to {offset} in cluster {cluster_id}")
                except Exception as e:
                    self._Logger.error(f"Error setting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Set offsets failed: Cluster {cluster_id} not found.")

        def checkHealth(self, cluster_id: str):
            if cluster_id in self._Clusters:
                try:
                    admin_client = self._Clusters[cluster_id]["admin_client"]
                    if admin_client:
                        brokers = admin_client.describe_cluster().brokers
                        if brokers:
                            self._Logger.info(f"Cluster {cluster_id} health check passed. Brokers: {brokers}")
                            return True
                        else:
                            self._Logger.warning(f"No brokers found in the cluster {cluster_id}.")
                    else:
                        self._Logger.error(f"Check health failed: No admin client found for cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Error during health check for cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Check health failed: Cluster {cluster_id} not found.")
            return False
